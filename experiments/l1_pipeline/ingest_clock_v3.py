#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""clock_v3 수집본 → L1 입력 변환기 (형식 변환 어댑터)

왜 필요한가
-----------
수집 프로그램(clock_v3, 개정판 3.2)은 원시 RGB-D를 **NPZ**로 저장하고 랜드마크를 **세로형**으로 기록한다.
반면 계산기(L1, `k1k2_from_files.py`)는 **16비트 PNG(mm)** · **가로형 랜드마크 표** · **최상위 intrinsics meta.json** 을 요구한다.
이 스크립트가 그 간극을 메운다. (계획서 §6, D-15/D-16 후속)

입력 (clock_v3 세션 폴더)
-------------------------
  <세션>/<pre>_metadata.json          # camera_info.color_intrinsics(fx,fy,ppx,ppy), depth_scale_m
  <세션>/<pre>_landmarks.csv          # Frame_ID,time_s,Hand,Landmark_ID,Landmark,Pixel_U,Pixel_V,...,RS_Status
  <세션>/<pre>_trials_summary.csv     # Trial,Hand,Task,Start_s,End_s,...
  <세션>/raw_rgbd/<frame:09d>.npz     # depth_aligned_u16 (색상 정렬 깊이, 센서 단위)

출력 (L1 입력 규격)
-------------------
  <out>/meta.json                            # 최상위 fx,fy,cx,cy,depth_scale=1.0,fps,camera_model,width,height
  <out>/L1_track/<trial_id>_landmarks.csv    # frame,t_s,thumb_u,thumb_v,index_u,index_v,wrist_u,wrist_v,occlusion_state,edge_mixing_suspect
  <out>/L0_raw/<trial_id>_depth/<frame>.png  # 16비트, 값 = depth(mm)

주의
----
- `occlusion_state`(보임/가림)는 **앱이 만들지 않는 사람 주석 항목**이다 → 이 변환기는 빈 값으로 둔다.
- `edge_mixing_suspect`는 랜드마크 3점의 `RS_Status == 'depth_edge'` 여부로 유도(0/1).
- PNG는 값이 **mm** 이므로 `meta.json`의 `depth_scale`은 **1.0** 으로 둔다(이중 스케일 방지).

사용
----
    python experiments/l1_pipeline/ingest_clock_v3.py --session "<clock_v3 세션폴더>" --out data/H01
    python experiments/l1_pipeline/ingest_clock_v3.py --selftest
"""
from __future__ import annotations

import argparse, csv, glob, io, json, os, sys
import numpy as np

try:
    import cv2
    _HAVE_CV = True
except Exception:
    _HAVE_CV = False

# MediaPipe Hand Landmark 인덱스
WRIST, THUMB_TIP, INDEX_TIP = 0, 4, 8
NEED = {WRIST: "wrist", THUMB_TIP: "thumb", INDEX_TIP: "index"}
PNG_COLS = ["frame", "t_s", "thumb_u", "thumb_v", "index_u", "index_v",
            "wrist_u", "wrist_v", "occlusion_state", "edge_mixing_suspect"]


def _read_csv(path):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _find_one(folder, suffix):
    hits = sorted(glob.glob(os.path.join(folder, "*" + suffix)))
    return hits[0] if hits else None


def _fnum(v):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _inum(v):
    x = _fnum(v)
    return None if x is None else int(round(x))


def load_meta(session):
    p = _find_one(session, "_metadata.json")
    with io.open(p, encoding="utf-8") as f:
        meta = json.load(f)
    ci = (meta.get("camera_info") or {}).get("color_intrinsics") or {}
    if not ci:
        raise ValueError("camera_info.color_intrinsics 없음: %s" % p)
    scale = (meta.get("camera_info") or {}).get("depth_scale_m") or 0.001
    return dict(fx=float(ci["fx"]), fy=float(ci["fy"]),
                cx=float(ci.get("ppx", ci.get("cx"))), cy=float(ci.get("ppy", ci.get("cy"))),
                width=int(ci.get("width") or 0), height=int(ci.get("height") or 0),
                depth_scale_m=float(scale))


def load_trials(session):
    p = _find_one(session, "_trials_summary.csv")
    rows = _read_csv(p)
    out = []
    for r in rows:
        s, e = _fnum(r.get("Start_s")), _fnum(r.get("End_s"))
        if s is None or e is None:
            continue
        out.append({"trial": str(r.get("Trial", "")).strip(), "hand": str(r.get("Hand", "")).strip(),
                    "task": str(r.get("Task", "")).strip(), "start": s, "end": e})
    return out


def trial_id_of(task, hand, trial):
    """예: Task 1 -> T1, Trial_3 -> t03, Right -> R"""
    t = task.split(":")[0].strip().replace("Task", "").strip() or "T"
    tn = "".join(ch for ch in trial if ch.isdigit()) or "1"
    hs = {"Right": "R", "Left": "L"}.get(hand, hand[:1] or "X")
    return "T%s_%s_t%s" % (t, hs, tn.zfill(2))


def load_landmarks(session):
    """세로형 → {frame_id: {'t_s':.., 'hand':.., 'uv':{idx:(u,v)}, 'edge':0/1}}"""
    p = _find_one(session, "_landmarks.csv")
    rows = _read_csv(p)
    frames = {}
    for r in rows:
        fid = _inum(r.get("Frame_ID"))
        lid = _inum(r.get("Landmark_ID"))
        if fid is None or lid is None:
            continue
        rec = frames.setdefault(fid, {"t_s": _fnum(r.get("time_s")), "hand": str(r.get("Hand", "")).strip(),
                                      "uv": {}, "edge": 0})
        if lid in NEED:
            u, v = _fnum(r.get("Pixel_U")), _fnum(r.get("Pixel_V"))
            rec["uv"][lid] = (u, v) if (u is not None and v is not None) else None
            if str(r.get("RS_Status", "")).strip() == "depth_edge":
                rec["edge"] = 1
    return frames


def _imwrite16(path, arr):
    """16비트 PNG 저장(비ASCII 경로 안전): cv2.imencode + tofile."""
    if not _HAVE_CV:
        raise RuntimeError("cv2 필요")
    ok, buf = cv2.imencode(".png", arr.astype(np.uint16))
    if not ok:
        raise RuntimeError("PNG 인코딩 실패: %s" % path)
    buf.tofile(path)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise RuntimeError("PNG 저장 실패: %s" % path)


def _npz_path(session, frame_id):
    p = os.path.join(session, "raw_rgbd", "%09d.npz" % int(frame_id))
    return p if os.path.exists(p) else None


def convert(session, out_dir, edge_from_status=True):
    if not _HAVE_CV:
        raise RuntimeError("cv2 필요(깊이 PNG 저장). 설치: pip install opencv-python")
    m = load_meta(session)
    trials = load_trials(session)
    frames = load_landmarks(session)
    os.makedirs(out_dir, exist_ok=True)
    # meta.json (L1: 최상위 fx/fy/cx/cy, depth_scale=1.0 ← PNG가 mm이므로)
    meta_out = dict(fx=m["fx"], fy=m["fy"], cx=m["cx"], cy=m["cy"], depth_scale=1.0,
                    fps=None, camera_model="RealSense D455 (aligned)",
                    width=m["width"], height=m["height"], aligned_to="color",
                    source="ingest_clock_v3", source_session=os.path.basename(os.path.abspath(session.rstrip("/\\"))),
                    note="L0_raw PNG 값 = depth(mm). depth_scale=1.0 (센서 depth_scale_m=%g 반영 완료)" % m["depth_scale_m"])
    with io.open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_out, f, ensure_ascii=False, indent=1)

    made, depth_n, lm_n, missing_depth = [], 0, 0, 0
    for tr in trials:
        tid = trial_id_of(tr["task"], tr["hand"], tr["trial"])
        sub_lm = os.path.join(out_dir, "L1_track"); os.makedirs(sub_lm, exist_ok=True)
        sub_d = os.path.join(out_dir, "L0_raw", tid + "_depth"); os.makedirs(sub_d, exist_ok=True)
        picked = []
        for fid in sorted(frames):
            rec = frames[fid]
            if rec["hand"] != tr["hand"]:
                continue
            if rec["t_s"] is None or not (tr["start"] <= rec["t_s"] <= tr["end"]):
                continue
            picked.append(fid)
            # 깊이 PNG
            npz = _npz_path(session, fid)
            if npz is None:
                missing_depth += 1
            else:
                z = np.load(npz, allow_pickle=False)
                d = z["depth_aligned_u16"].astype(np.float64) * m["depth_scale_m"] * 1000.0  # mm
                d[~np.isfinite(d) | (d < 0)] = 0
                _imwrite16(os.path.join(sub_d, "%d.png" % fid), np.round(d).astype(np.uint16))
                depth_n += 1
        if not picked:
            continue
        with io.open(os.path.join(sub_lm, tid + "_landmarks.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(PNG_COLS)
            for fid in picked:
                rec = frames[fid]
                uv = rec["uv"]
                def px(i):
                    q = uv.get(i)
                    return (q[0], q[1]) if q else ("", "")
                tu, tv = px(THUMB_TIP); iu, iv = px(INDEX_TIP); wu, wv = px(WRIST)
                w.writerow([fid, "" if rec["t_s"] is None else "%.6f" % rec["t_s"],
                            "" if tu == "" else "%.2f" % tu, "" if tv == "" else "%.2f" % tv,
                            "" if iu == "" else "%.2f" % iu, "" if iv == "" else "%.2f" % iv,
                            "" if wu == "" else "%.2f" % wu, "" if wv == "" else "%.2f" % wv,
                            "", rec["edge"] if edge_from_status else 0])
            lm_n += 1
        made.append(tid)
    return dict(trials=len(made), trial_ids=made, landmarks_files=lm_n,
                depth_pngs=depth_n, missing_depth_frames=missing_depth, out=out_dir, meta=meta_out)


# ===========================================================================
# 자체 시험: 합성 clock_v3 세션을 만들어 변환 → L1 실행까지 확인
# ===========================================================================
def _build_fake_session(root, w=640, h=480, fx=600.0, n=20, depth_mm=500):
    os.makedirs(os.path.join(root, "raw_rgbd"), exist_ok=True)
    meta = {"camera_info": {"color_intrinsics": {"width": w, "height": h, "fx": fx, "fy": fx,
                                                 "ppx": w / 2.0, "ppy": h / 2.0},
                            "depth_scale_m": 0.001}}
    with io.open(os.path.join(root, "S_test_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    # 랜드마크: wrist(320,240), thumb(400,240), index(500,240) → thumb-index 100px = 83.3 mm
    with io.open(os.path.join(root, "S_test_landmarks.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w_ = csv.writer(f)
        w_.writerow(["Frame_ID", "time_s", "Hand", "Landmark_ID", "Landmark", "Pixel_U", "Pixel_V",
                     "MP_X_m", "MP_Y_m", "MP_Z_m", "RS_X_m", "RS_Y_m", "RS_Z_m", "RS_Depth_m", "RS_Status"])
        for i in range(n):
            for lid, (u, v) in ((0, (320, 240)), (4, (400, 240)), (8, (500, 240))):
                w_.writerow([i, "%.6f" % (i / 30.0), "Right", lid, "", u, v, 0, 0, 0, 0, 0, 0, depth_mm, "ok"])
    with io.open(os.path.join(root, "S_test_trials_summary.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w_ = csv.writer(f)
        w_.writerow(["Trial", "Hand", "Task", "Trial_Mode", "Start_s", "End_s", "Duration_s", "Cycles"])
        w_.writerow(["Trial_1", "Right", "Task 1: 맨손", "manual", "0.0", "%.3f" % (n / 30.0), "0.6", "1"])
    for i in range(n):
        arr = np.full((h, w), depth_mm, dtype=np.uint16)   # 센서 단위 = mm (scale 0.001)
        np.savez(os.path.join(root, "raw_rgbd", "%09d.npz" % i),
                 color_bgr=np.zeros((h, w, 3), np.uint8), depth_aligned_u16=arr,
                 metadata_json=np.asarray(json.dumps({"frame_id": i})))
    return root


def selftest():
    import tempfile, shutil
    ok = True
    def chk(name, cond, detail=""):
        nonlocal ok
        print("  %-52s %s %s" % (name, "PASS" if cond else "FAIL", detail)); ok = ok and bool(cond)

    tmp = tempfile.mkdtemp()
    try:
        src = _build_fake_session(os.path.join(tmp, "src"))
        out = os.path.join(tmp, "out")
        res = convert(src, out)
        chk("meta.json 생성", os.path.exists(os.path.join(out, "meta.json")))
        mo = json.load(io.open(os.path.join(out, "meta.json"), encoding="utf-8"))
        chk("meta 최상위 fx/cx 존재", mo.get("fx") == 600.0 and abs((mo.get("cx") or 0) - 320) < 1e-6, str({k: mo.get(k) for k in ('fx','cx')}))
        chk("depth_scale=1.0 (PNG가 mm)", mo.get("depth_scale") == 1.0, str(mo.get("depth_scale")))
        lm = glob.glob(os.path.join(out, "L1_track", "*_landmarks.csv"))
        chk("L1_track 랜드마크 파일 생성", len(lm) == 1, str([os.path.basename(x) for x in lm]))
        rows = _read_csv(lm[0])
        chk("가로형 헤더", list(rows[0].keys()) == PNG_COLS, str(list(rows[0].keys())))
        chk("행 수 = 프레임 수", len(rows) == 20, str(len(rows)))
        pngs = glob.glob(os.path.join(out, "L0_raw", "*_depth", "*.png"))
        chk("깊이 PNG 생성", len(pngs) == 20, str(len(pngs)))
        if _HAVE_CV:
            z = cv2.imdecode(np.fromfile(pngs[0], dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            chk("PNG 값 = 500 mm (u16)", int(z[0, 0]) == 500, str(int(z[0, 0])))
        # --- L1 실행까지 ---
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import importlib
            L1 = importlib.import_module("k1k2_from_files")
            meta = L1.load_meta(out)
            trecs = []
            for p in sorted(glob.glob(os.path.join(out, "L1_track", "*_landmarks.csv"))):
                tid = os.path.basename(p).replace("_landmarks.csv", "")
                trecs.append(L1.process_trial(out, meta, tid, depth_scale=meta.get("depth_scale", 1.0)))
            chk("L1이 변환본을 읽고 K1 계산", len(trecs) == 1, str(len(trecs)))
            if trecs:
                k1 = trecs[0].get("k1_thumb_index_surface_p95_mm")
                chk("K1 ≈ 83.3 mm (합성 기대값)", k1 is not None and abs(k1 - 83.33) < 2.0, str(k1))
        except Exception as e:
            chk("L1 실행", False, "예외: %s" % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("")
    print("자체 시험 종합: %s" % ("ALL PASS" if ok else "FAIL 있음"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session"); ap.add_argument("--out", default="data/H01")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return 0 if selftest() else 1
    if not a.session:
        print(__doc__); return 0
    r = convert(a.session, a.out)
    print("변환 완료 → %s" % r["out"])
    print("  trial %d개 | 랜드마크 파일 %d | 깊이 PNG %d | 깊이 누락 프레임 %d"
          % (r["trials"], r["landmarks_files"], r["depth_pngs"], r["missing_depth_frames"]))
    print("  다음: python experiments/l1_pipeline/k1k2_from_files.py --session \"%s\"" % r["out"])
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
