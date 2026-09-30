# -*- coding: utf-8 -*-
"""앱(clock_v3) 산출물 → L2 지표 JSON 빌더 (신 지표 M1·M2·M3·M4).

입력(세션 폴더):
  * _landmarks.csv        프레임별 랜드마크 (MP_X/Y/Z, RS_*, RS_Status)
  * _continuous_raw.csv   프레임별 각도(_raw/_filt) + time_s + Trial + hand
  * _trials_summary.csv   시행 요약(TAM_total_deg, Duration_s ...)
출력:
  <세션>/L2_metric/<trial>_<hand>.json

지표(계획서 §7.6):
  M1 = K1_mp  : 엄지끝(4)·검지끝(8) **MediaPipe world landmark** 3D 거리의 P95 (mm)
  M2 = TAM_total : 앱 trials_summary.TAM_total_deg (deg) — 읽기만
  M3 = MGA    : 같은 시계열의 max (mm) — 보조·기록용
  M4 = SPARC  : 4손가락 PIP(_filt) 평균 → 보수적 균일격자 → sparc_ref.sparc()

사용: python experiments/metrics/l2_from_app.py --session "<세션폴더>" [--out ...]
      python experiments/metrics/l2_from_app.py --selftest
작성 2026-09-30. 읽기 전용(원자료 수정 없음).
"""
import argparse
import csv
import glob
import io
import json
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sparc_ref import sparc_uniform  # noqa: E402

PIPS = ("Index_PIP", "Middle_PIP", "Ring_PIP", "Pinky_PIP")
TIP_THUMB, TIP_INDEX = "4", "8"
Q3_MIN_SAMPLES = 50          # 유효 프레임 하한(계획서 §7.3)
Q2_MAX_GAP_S = 0.3           # 최장 결측 상한
APERTURE_CAP_MM = 150.0      # MGA 상한(앱 APERTURE_MAX_MM) — 초과 프레임은 max에서 제외
MGA_CAP_FRAC_MAX = 0.05      # 캡된 비율이 이보다 크면 M1 보류


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def p95(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    pos = 0.95 * (len(v) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] * (1 - (pos - lo)) + v[hi] * (pos - lo)


def d3(a, b):
    if None in a or None in b:
        return None
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def read_first(sess, suffix):
    fs = glob.glob(os.path.join(sess, "*" + suffix))
    return fs[0] if fs else None


def load_app(sess):
    """반환: {trial: {'hand', 't_range', 'T', 'tam', 'sparc', 'series'}} + landmarks."""
    cont = read_first(sess, "_continuous_raw.csv")
    summ = read_first(sess, "_trials_summary.csv")
    lms = read_first(sess, "_landmarks.csv")
    if not (cont and lms):
        raise FileNotFoundError("continuous_raw.csv / landmarks.csv 필요")

    trials = {}
    with io.open(cont, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            tr, hand = r.get("Trial"), r.get("hand")
            if not tr or tr.lower() == "rest":
                continue
            t = fnum(r.get("time_s"))
            if t is None:
                continue
            d = trials.setdefault((tr, hand), {"t": [], "pip": []})
            d["t"].append(t)
            vs = [fnum(r.get(f"{j}_filt")) for j in PIPS]
            d["pip"].append(float(np.mean(vs)) if all(v is not None for v in vs) else None)

    tam = {}
    if summ:
        with io.open(summ, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                tr = (r.get("Trial") or "").replace("Trial #", "Trial_").strip()
                tam[(tr, r.get("Hand"))] = {
                    "tam": fnum(r.get("TAM_total_deg")),
                    "T": fnum(r.get("Duration_s")),
                    "sparc_app": fnum(r.get("SPARC")),
                }

    lm = {}
    with io.open(lms, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            lid = r.get("Landmark_ID")
            if lid not in (TIP_THUMB, TIP_INDEX):
                continue
            key = (r.get("Hand"), fnum(r.get("time_s")))
            if key[1] is None:
                continue
            lm.setdefault(key, {})[lid] = (
                fnum(r.get("MP_X_m")), fnum(r.get("MP_Y_m")), fnum(r.get("MP_Z_m")),
                (r.get("RS_Status") or "").strip())
    return trials, tam, lm


def build(sess):
    trials, tam, lm = load_app(sess)
    # 손별 시행 시간구간
    ranges = {}
    for (tr, hand), d in trials.items():
        if d["t"]:
            ranges[(tr, hand)] = (min(d["t"]), max(d["t"]))

    out = []
    for (tr, hand), d in sorted(trials.items()):
        t0, t1 = ranges[(tr, hand)]
        tip_dists, mp_ok, rs_edge, n_frames = [], 0, 0, 0
        for (h, t), pts in lm.items():
            if h != hand or t is None or not (t0 - 1e-6 <= t <= t1 + 1e-6):
                continue
            n_frames += 1
            if TIP_THUMB in pts and TIP_INDEX in pts:
                a, b = pts[TIP_THUMB], pts[TIP_INDEX]
                dd = d3(a[:3], b[:3])
                if dd is not None:
                    tip_dists.append(dd * 1000.0)
                    mp_ok += 1
                if a[3] == "depth_edge" or b[3] == "depth_edge":
                    rs_edge += 1

        # 최장 결측(유효 M1 프레임 사이 시간)
        times = sorted(t for (h, t), pts in lm.items()
                       if h == hand and t is not None and t0 <= t <= t1
                       and TIP_THUMB in pts and TIP_INDEX in pts
                       and d3(pts[TIP_THUMB][:3], pts[TIP_INDEX][:3]) is not None)
        max_gap = 0.0
        for a, b in zip(times, times[1:]):
            max_gap = max(max_gap, b - a)

        # M1 = MGA (max, 150mm 캡) · M3 = K1_mp (P95, 로버스트 민감도)
        capped = [d for d in tip_dists if d > APERTURE_CAP_MM]
        capped_frac = (len(capped) / len(tip_dists)) if tip_dists else 0.0
        kept = [d for d in tip_dists if d <= APERTURE_CAP_MM]
        m1 = max(kept) if kept else None
        m3 = p95(tip_dists)
        info = tam.get((tr, hand), {})
        m2 = info.get("tam")
        sp = sparc_uniform(d["t"], d["pip"])
        m4, sparc_fs, sparc_status = sp
        T = info.get("T") if info.get("T") is not None else (t1 - t0)

        q = {
            "n_frames": n_frames,
            "m1_valid_frames": len(tip_dists),
            "m1_valid_ratio": round(len(tip_dists) / n_frames, 4) if n_frames else 0.0,
            "max_gap_s": round(max_gap, 4),
            "rs_edge_frac": round(rs_edge / n_frames, 4) if n_frames else 0.0,
            "mga_capped_frames": len(capped),
            "mga_capped_frac": round(capped_frac, 4),
            "sparc_fs_hz": round(sparc_fs, 3) if sparc_fs else None,
            "sparc_status": sparc_status,
            "time_monotonic": bool(len(d["t"]) > 1 and np.all(np.diff(d["t"]) > 0)),
            "app_sparc": info.get("sparc_app"),
        }
        ok_m1 = len(tip_dists) >= Q3_MIN_SAMPLES and capped_frac <= MGA_CAP_FRAC_MAX
        ok_m2 = m2 is not None
        ok_m4 = m4 is not None
        rec = {
            "trial_id": "%s_%s" % (tr, hand),
            "trial": tr, "hand": hand,
            "observation_window_s": round(T, 4) if T else None,
            "m1_mga_mm": None if m1 is None else round(m1, 3),
            "m2_tam_total_deg": m2,
            "m3_k1mp_p95_mm": None if m3 is None else round(m3, 3),
            "m4_sparc": None if m4 is None else round(m4, 4),
            "q": q,
            "available": {"m1": bool(ok_m1), "m2": bool(ok_m2),
                          "m3": bool(m3 is not None and len(tip_dists) >= Q3_MIN_SAMPLES),
                          "m4": bool(ok_m4)},
            "reasons": {k: [] for k in ("m1", "m2", "m4")},
        }
        if not ok_m1:
            rec["reasons"]["m1"].append("Q3(%d<%d) or cap%.3f>%.2f"
                                     % (len(tip_dists), Q3_MIN_SAMPLES, capped_frac, MGA_CAP_FRAC_MAX))
        if max_gap > Q2_MAX_GAP_S:
            rec["reasons"]["m1"].append("Q2(gap %.2fs)" % max_gap)
            rec["available"]["m1"] = False
            rec["available"]["m3"] = False
        if not ok_m2:
            rec["reasons"]["m2"].append("TAM 결측")
        if not ok_m4:
            rec["reasons"]["m4"].append("sparc:%s" % sparc_status)
        out.append(rec)
    return out


def write_l2(sess, recs):
    d = os.path.join(sess, "L2_metric")
    os.makedirs(d, exist_ok=True)
    for r in recs:
        p = os.path.join(d, r["trial_id"].replace(" ", "") + ".json")
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
    return d


# --------------------------------------------------------------------------
def _write_synth(root, n=80, fps=13.4, gap_from=30, gap_to=45):
    os.makedirs(root)
    t = np.arange(n) / fps
    with io.open(os.path.join(root, "S_x_continuous_raw.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "Task", "Trial", "hand"] + [f"{j}_filt" for j in PIPS])
        ang = 20.0 + 25.0 * np.sin(2 * np.pi * 1.2 * t)
        for i in range(n):
            w.writerow(["%.6f" % t[i], "Task 1", "Trial_1", "Left"] + ["%.4f" % ang[i]] * len(PIPS))
    with io.open(os.path.join(root, "S_x_landmarks.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Frame_ID", "time_s", "Hand", "Landmark_ID", "Landmark",
                    "Pixel_U", "Pixel_V", "MP_X_m", "MP_Y_m", "MP_Z_m",
                    "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Depth_m", "RS_Status"])
        for i in range(n):
            ok = not (gap_from <= i < gap_to)
            ap = 0.060 + 0.020 * math.sin(2 * math.pi * 0.8 * t[i])
            for lid, off in ((TIP_THUMB, -ap / 2), (TIP_INDEX, +ap / 2)):
                mp = "%.6f" % off if ok else ""      # 결측 구간은 MP도 비운다(M1은 MP 기반)
                w.writerow([i, "%.6f" % t[i], "Left", lid, "x",
                            "", "", mp, "0.0" if ok else "", "0.0" if ok else "",
                            "%.6f" % off if ok else "", "0.0", "0.0",
                            "0.4" if ok else "", "ok" if ok else "depth_hole"])
    with io.open(os.path.join(root, "S_x_trials_summary.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Trial", "Hand", "TAM_total_deg", "Duration_s", "SPARC"])
        w.writerow(["Trial #1", "Left", "742.35", "%.4f" % (n / fps), "-3.1"])
    return root


def selftest():
    ok_all, log = True, []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-52s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    base = tempfile.mkdtemp(prefix="l2app_")
    try:
        r = _write_synth(os.path.join(base, "s1"), n=80)
        recs = build(r)
        chk("시행 1건 생성", len(recs) == 1, str(len(recs)))
        a = recs[0]
        chk("M1(MGA, max) ≥ M3(P95)", a["m1_mga_mm"] >= a["m3_k1mp_p95_mm"],
            "%s >= %s" % (a["m1_mga_mm"], a["m3_k1mp_p95_mm"]))
        chk("M1 이 55–95mm 범위(MGA≈60±20 캡 적용)", 55 <= a["m1_mga_mm"] <= 95,
            str(a["m1_mga_mm"]))
        chk("캡 기록(q.mga_capped_frames)", "mga_capped_frames" in a["q"], str(a["q"].get("mga_capped_frames")))
        chk("M2 = 앱 TAM 그대로", a["m2_tam_total_deg"] == 742.35, str(a["m2_tam_total_deg"]))
        chk("M3 = P95 ≤ M1", a["m3_k1mp_p95_mm"] <= a["m1_mga_mm"],
            "%s <= %s" % (a["m3_k1mp_p95_mm"], a["m1_mga_mm"]))
        chk("M4(SPARC) 계산됨(≤0)", a["m4_sparc"] is not None and a["m4_sparc"] <= 0,
            str(a["m4_sparc"]))
        chk("15프레임 MP 결측 → Q2로 m1 보류", a["available"]["m1"] is False
            and any("Q2" in x for x in a["reasons"]["m1"]), str(a["reasons"]["m1"]))
        chk("m2·m4는 가용", a["available"]["m2"] and a["available"]["m4"])
        d = write_l2(r, recs)
        chk("L2_metric/*.json 저장", len(glob.glob(os.path.join(d, "*.json"))) == 1)

        r2 = _write_synth(os.path.join(base, "s2"), n=80, gap_from=1, gap_to=1)
        a2 = build(r2)[0]
        chk("결측 없으면 m1 가용", a2["available"]["m1"] is True, str(a2["reasons"]["m1"]))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    return ok_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return 0 if selftest() else 1
    if not a.session:
        print(__doc__)
        return 1
    sess = a.session.rstrip("/\\")
    recs = build(sess)
    print("%-28s %10s %10s %10s %8s %8s" % ("trial", "M1MGA(mm)", "M2(deg)", "M4", "n", "avail"))
    for r in recs:
        print("%-28s %10s %10s %10s %8d %8s" % (
            r["trial_id"],
            r["m1_mga_mm"], r["m2_tam_total_deg"], r["m4_sparc"],
            r["q"]["m1_valid_frames"],
            "".join("1" if r["available"][k] else "0" for k in ("m1", "m2", "m4"))))
    if a.write:
        d = write_l2(sess, recs)
        print("[saved] %s (%d files)" % (d, len(recs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
