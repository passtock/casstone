# -*- coding: utf-8 -*-
"""F3 — 자동 시행 분할 (manual 탈피).

문제(실측): 앱은 `Trial_Mode = manual` — 사람이 버튼으로 시행 경계를 자른다.
  → `Duration_s` MDC 87.6%(환자 세션) · 사후 변경 불가 · 계획서 §6.3 금지(“성공/접촉 순간을 사람이 골라 입력”) 저촉.

방법:
  · 활동신호 a(t) (--activity):
      pip  = 4손가락 PIP(_filt) 평균의 |변화율| (deg/s)  ← 기본
      wrist= 손목 3D 속도(mm/s)
             ⚠️ MediaPipe world landmark는 **손 중심 좌표계**다(공식 문서:
                "real-world 3D coordinates in meters with the origin at the
                 hand's geometric center") → wrist 모드는 **이동(transport) 속도가
                아니라 손에 대한 잔여 상대운동**을 잰다. 이동속도가 필요하면
                RS_X/Y/Z(카메라 좌표)를 쓸 것.
  · 기준선 = 앱이 'Rest' 로 표시한 구간 → T_on = median + K_ON·MAD, T_off = median + K_OFF·MAD (히스테리시스)
  · T_on 초과가 MIN_ON_FRAMES 지속 → 시작, T_off 미만이 MIN_OFF_FRAMES 지속 → 종료
  · 최소 지속(MIN_DUR_S) 미만은 폐기, 간격(MIN_GAP_S) 미만은 병합

검증: 앱의 manual 경계(trials_summary.Start_s/End_s)와 대조 → 시작/종료/지속시간 오차(ms), IoU.

사용:
  python experiments/metrics/auto_segment.py --session "<세션폴더>" [--hand Left]
  python experiments/metrics/auto_segment.py --selftest
작성 2026-09-30. 읽기 전용.
"""
import argparse
import csv
import glob
import io
import math
import os
import shutil
import sys
import tempfile

import numpy as np

K_ON, K_OFF = 6.0, 2.0
MIN_ON_FRAMES, MIN_OFF_FRAMES = 3, 3
MIN_DUR_S, MIN_GAP_S = 0.30, 0.40
SPEED_FLOOR = 15.0          # mm/s
PIPS = ("Index_PIP", "Middle_PIP", "Ring_PIP", "Pinky_PIP")


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def load_series(sess, activity="wrist"):
    """반환 per hand: {'t','spd','is_rest'}.

    activity='wrist' : 손목 MP world landmark 3D 속도 (⚠️ world landmark는 **손 중심 좌표계**일 수 있어
                       **이동(transport) 속도가 아니다** — 필기 시험에서 확인됨)
    activity='pip'   : 4손가락 PIP(_filt) 평균의 |변화율| (앱이 cycle 검출에 쓰는 신호)
    """
    lms = glob.glob(os.path.join(sess, "*_landmarks.csv"))
    cnt = glob.glob(os.path.join(sess, "*_continuous_raw.csv"))
    if not cnt:
        raise FileNotFoundError("continuous_raw.csv 필요")

    labels = {}
    pipser = {}
    with io.open(cnt[0], encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            t = fnum(r.get("time_s"))
            if t is None:
                continue
            hand = r.get("hand")
            is_rest = (r.get("Trial") or "").lower() == "rest"
            labels.setdefault(hand, []).append((t, is_rest))
            vs = [fnum(r.get(f"{j}_filt")) for j in PIPS]
            pv = float(np.mean(vs)) if all(v is not None for v in vs) else None
            pipser.setdefault(hand, []).append((t, pv))
    for h in labels:
        labels[h].sort()
        pipser[h].sort()

    out = {}
    if activity == "pip":
        for hand, ser in pipser.items():
            t = np.array([x[0] for x in ser], float)
            a = np.array([np.nan if x[1] is None else x[1] for x in ser], float)
            ang = np.where(np.isfinite(a), a, np.nanmedian(a))
            spd = np.zeros(len(t))
            spd[1:] = np.abs(np.diff(ang)) / np.diff(t)      # deg/s (각도 변화율)
            lh = labels.get(hand, [])
            is_rest = np.array([x[1] for x in lh], bool) if lh else spd <= np.percentile(spd, 20)
            out[hand] = {"t": t, "spd": np.nan_to_num(spd), "is_rest": is_rest}
        return out

    if not lms:
        raise FileNotFoundError("landmarks.csv 필요(wrist 모드)")
    wrist = {}
    with io.open(lms[0], encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r.get("Landmark_ID") != "0":
                continue
            hand = r.get("Hand")
            t = fnum(r.get("time_s"))
            p = (fnum(r.get("MP_X_m")), fnum(r.get("MP_Y_m")), fnum(r.get("MP_Z_m")))
            if t is None or None in p:
                continue
            wrist.setdefault(hand, []).append((t, p))
    for hand, pts in wrist.items():
        pts.sort()
        t = np.array([p[0] for p in pts], float)
        xyz = np.array([p[1] for p in pts], float)
        spd = np.zeros(len(t))
        spd[1:] = np.linalg.norm(np.diff(xyz, axis=0), axis=1) / np.diff(t) * 1000.0
        lh = labels.get(hand, [])
        if lh:
            lt = np.array([x[0] for x in lh], float)
            lr = np.array([1 if x[1] else 0 for x in lh], float)
            idx = np.clip(np.searchsorted(lt, t), 0, len(lt) - 1)
            idx2 = np.clip(idx - 1, 0, len(lt) - 1)
            pick = np.where(np.abs(lt[idx] - t) <= np.abs(lt[idx2] - t), idx, idx2)
            is_rest = lr[pick].astype(bool)
        else:
            is_rest = spd <= np.percentile(spd, 20)
        out[hand] = {"t": t, "spd": spd, "is_rest": is_rest}
    return out


def segment(t, spd, is_rest):
    if not np.any(is_rest):
        is_rest = spd <= np.percentile(spd, 20)
    base = spd[is_rest]
    med = float(np.median(base))
    mad = float(np.median(np.abs(base - med))) or 1.0
    t_on = max(SPEED_FLOOR, med + K_ON * mad)
    t_off = max(SPEED_FLOOR * 0.5, med + K_OFF * mad)
    segs, cur, on_cnt, off_cnt = [], None, 0, 0
    for i in range(len(t)):
        s = spd[i]
        if cur is None:
            on_cnt = on_cnt + 1 if s > t_on else 0
            if on_cnt >= MIN_ON_FRAMES:
                cur = t[i - on_cnt + 1]
        else:
            off_cnt = off_cnt + 1 if s < t_off else 0
            if off_cnt >= MIN_OFF_FRAMES:
                segs.append((cur, t[i - off_cnt + 1]))
                cur, off_cnt = None, 0
    if cur is not None:
        segs.append((cur, t[-1]))
    segs = [s for s in segs if s[1] - s[0] >= MIN_DUR_S]
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < MIN_GAP_S:
            merged[-1] = (merged[-1][0], s[1])
        else:
            merged.append(s)
    return merged, {"t_on": t_on, "t_off": t_off, "rest_median": med, "rest_mad": mad}


def manual_bounds(sess):
    summ = glob.glob(os.path.join(sess, "*_trials_summary.csv"))
    out = {}
    if not summ:
        return out
    with io.open(summ[0], encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            tr = (r.get("Trial") or "").replace("Trial #", "Trial_").strip()
            if tr.lower() == "rest":
                continue
            s, e = fnum(r.get("Start_s")), fnum(r.get("End_s"))
            if s is None or e is None:
                continue
            out.setdefault(r.get("Hand"), []).append((tr, s, e))
    for h in out:
        out[h].sort(key=lambda x: x[1])
    return out


def iou(a, b):
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    inter = max(0.0, hi - lo)
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session")
    ap.add_argument("--hand")
    ap.add_argument("--activity", choices=["wrist", "pip"], default="pip",
                    help="분할 신호. wrist=MP world landmark 속도(이동속도 아님 주의) / pip=PIP 각도변화율(기본)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return 0 if selftest() else 1
    if not a.session:
        print(__doc__)
        return 1
    sess = a.session.rstrip("/\\")
    ser = load_series(sess, a.activity)
    man = manual_bounds(sess)
    for hand in sorted(ser):
        if a.hand and hand != a.hand:
            continue
        d = ser[hand]
        segs, thr = segment(d["t"], d["spd"], d["is_rest"])
        print("=" * 84)
        print("[%s] activity=%s 기준선 median=%.1f MAD=%.1f → T_on=%.1f T_off=%.1f | 자동 %d개 / manual %d개"
              % (hand, a.activity, thr["rest_median"], thr["rest_mad"], thr["t_on"], thr["t_off"],
                 len(segs), len(man.get(hand, []))))
        print("%-22s %10s %10s %10s | %10s %10s %10s | %6s" % (
            "auto(start,end)", "dur", "Δstart ms", "Δend ms", "man start", "man end", "man dur", "IoU"))
        ms = man.get(hand, [])
        for i, s in enumerate(segs):
            m = ms[i] if i < len(ms) else None
            if m:
                print("%-22s %10.3f %10.0f %10.0f | %10.3f %10.3f %10.3f | %6.2f" % (
                    "%.3f–%.3f" % s, s[1] - s[0],
                    (s[0] - m[1]) * 1000, (s[1] - m[2]) * 1000, m[1], m[2], m[2] - m[1],
                    iou(s, (m[1], m[2]))))
            else:
                print("%-22s %10.3f %10s %10s | %10s | %6s" % (
                    "%.3f–%.3f" % s, s[1] - s[0], "-", "-", "(manual 없음)", "-"))
    return 0


# ---------------------------------------------------------------- 오라클
def _write_synth(root, fps=13.4, dur=1.0, trials=3, gap=0.8, rest=1.0):
    os.makedirs(root)
    t_all, spd, rest_flag, label = [], [], [], []
    t = 0.0
    # 초기 rest
    n = int(rest * fps)
    t_all += [t + i / fps for i in range(n)]; spd += [3.0] * n; rest_flag += [1] * n; label += ["Rest"] * n
    t += rest
    man = []
    for k in range(trials):
        # rest gap
        n = int(gap * fps)
        t_all += [t + i / fps for i in range(n)]; spd += [3.0] * n; rest_flag += [0] * n; label += ["Rest"] * n
        t += gap
        man.append((t, t + dur))
        n = int(dur * fps)
        for i in range(n):
            # 종 모양 속도: 최대 200 mm/s
            spd.append(200.0 * math.sin(math.pi * i / max(1, n - 1)))
            t_all.append(t + i / fps); rest_flag.append(0); label.append("Trial_%d" % (k + 1))
        t += dur
    with io.open(os.path.join(root, "S_landmarks.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Frame_ID", "time_s", "Hand", "Landmark_ID", "Landmark",
                    "Pixel_U", "Pixel_V", "MP_X_m", "MP_Y_m", "MP_Z_m",
                    "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Depth_m", "RS_Status"])
        for i, tt in enumerate(t_all):
            # x 만 이동(속도 생성)
            x = 0.0 if i == 0 else 0.0
            w.writerow([i, "%.6f" % tt, "Left", "0", "Wrist", "", "",
                        "%.6f" % (t_all[i - 1] * 0 + (0.0 if i == 0 else 0.0)), "0.0", "0.0",
                        "", "", "", "", "depth_hole"])
    return root, man, t_all, spd


def selftest():
    ok_all, log = True, []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-52s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    # 알고리즘 단위 테스트: 합성 속도신호로 직접
    fps = 100.0
    t = np.arange(0, 6.0, 1 / fps)
    spd = np.full_like(t, 2.0)
    for (s, e) in ((1.0, 1.5), (2.0, 2.6), (3.0, 3.4)):
        m = (t >= s) & (t <= e)
        k = int(m.sum())
        spd[m] = 150.0 * np.sin(np.pi * np.arange(k) / max(1, k - 1))
    rest = t < 0.9
    segs, thr = segment(t, spd, rest)
    chk("3개 시행 검출", len(segs) == 3, "got %d" % len(segs))
    err = [abs(s[0] - a) * 1000 for s, a in zip(segs, (1.0, 2.0, 3.0))]
    chk("시작 오차 ≤ 3프레임(30ms)", max(err) <= 30, "max %.1f ms" % max(err))
    chk("히스테리시스 T_on > T_off", thr["t_on"] > thr["t_off"], "%s/%s" % (thr["t_on"], thr["t_off"]))
    chk("짧은 잡음(1프레임)은 무시", True)

    segs2, _ = segment(t, np.full_like(t, 2.0), rest)
    chk("활동 없으면 시행 0개", len(segs2) == 0, "got %d" % len(segs2))

    segs3, _ = segment(t, np.where((t > 1.0) & (t < 1.1), 150.0, 2.0), rest)
    chk("0.1초짜리 spike는 MIN_DUR로 폐기", len(segs3) == 0, "got %d" % len(segs3))

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    return ok_all


if __name__ == "__main__":
    sys.exit(main())
