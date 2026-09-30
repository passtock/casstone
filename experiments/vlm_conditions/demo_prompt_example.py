# -*- coding: utf-8 -*-
"""A2/A3 프롬프트 실물 예시 생성 (합성 데이터). 2026-09-30.
목적: '무엇이 AI에게 들어가는가'를 실제 문자열로 확인."""
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))  # experiments/


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


k1k2 = load("k1k2mod", os.path.join(HERE, "l1_pipeline", "k1k2_from_files.py"))
mc = load("mcmod", os.path.join(HERE, "vlm_conditions", "make_conditions_v6.py"))

base = tempfile.mkdtemp(prefix="demo_prompt_")
try:
    ra = os.path.join(base, "A_clean")
    os.makedirs(ra)
    k1k2._write_synthetic_session(ra, n=80, thumb_index_mm=15.0, step_px=3.0)
    recs_a, _ = k1k2.process_session(ra, q1_min=0.3, write=True)

    rb = os.path.join(base, "B_gap")
    os.makedirs(rb)
    k1k2._write_synthetic_session(rb, n=80, thumb_index_mm=15.0, step_px=3.0,
                                  gap_frames=(20, 32))
    recs_b, _ = k1k2.process_session(rb, q1_min=0.3, write=True)

    sess = recs_a + recs_b
    sess[1]["task"] = "T2"

    print("=" * 78)
    print("[1] 시행별로 '계산'되는 값  (Q1~Q4는 모델에게 주는 값이 아니라 '심사위원')")
    print("=" * 78)
    for i, r in enumerate(sess):
        q = r["q"]
        print("")
        print("[시행 %d] %s" % (i + 1, r["trial_id"]))
        print("  K1 원값 = %s mm      K2 원값 = %s mm/s" % (r.get("k1_raw_mm"), r.get("k2_raw_mm")))
        print("  K1 Q통과 = %s      K2 Q통과 = %s   <- A3가 쓰는 값" % (
            r.get("k1_thumb_index_surface_p95_mm"), r.get("k2_wrist_surface_speed_p95_mm_s")))
        print("  Q1 depth유효율=%.3f (>=0.3)  Q2 최장결측=%.3fs (<=0.3)  "
              "Q3 유효표본=%d,%d (>=50)  Q4 경계혼합=%.3f (<=0.5)" % (
                  q["q1_pair_valid_ratio"], q["q2_max_gap_s"],
                  q["q3_valid_samples_k1"], q["q3_valid_samples_k2"],
                  q["q4_edge_mixing_frac"]))
        print("  => 판정 k1=%s k2=%s  reasons=%s" % (
            r["usable"]["k1"], r["usable"]["k2"],
            (r["usable"]["reasons_k1"] or r["usable"]["reasons_k2"])))

    print("")
    print("=" * 78)
    print("[2] AI에게 실제로 들어가는 프롬프트 (조건별, 같은 조건 2시행)")
    print("=" * 78)
    u = mc.estimate_u(sess, "ratio", (0.10, 0.30))
    rows = mc.make_rows(sess, u=u, burst_trial_index=99)
    seen = {}
    for r in rows:
        if r["injection"] != "none" or r["r_seed"] != "":
            continue
        b = seen.setdefault(r["condition"], [])
        if r["prompt"] not in b and len(b) < 2:
            b.append(r["prompt"])
    for cond in ("A1", "A2", "A3", "A4"):
        for i, p in enumerate(seen.get(cond, [])):
            print("")
            print("-" * 78)
            print("조건 %s  (그 조건의 서로 다른 시행 %d/2)" % (cond, i + 1))
            print("-" * 78)
            print(p.rstrip())
finally:
    shutil.rmtree(base, ignore_errors=True)
