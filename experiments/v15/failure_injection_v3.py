# -*- coding: utf-8 -*-
"""실패주입·오검출 v3 — 독립 검토보고서 지적을 반영해 **내 v2 오류를 바로잡은** 재계산.

v2(`failure_injection.py`)의 3가지 오류 (검토보고서 §5, 2026-10-02)
  O1. 저장 키가 `group|hand` 라서 **환자 두 세션이 서로 덮어썼다**(미사가 애프터로 교체).
  O2. 시행 판정을 `flags.any()`(한 프레임만 위반해도 탈락)로 계산했다.
      계획서 §8.2의 실제 규칙은 **검사 가능한 프레임 중 위반 비율이 상한(잠정 30%) 초과**다.
  O3. 주입 구간의 위반을 **주입 전 위반과 빼지 않고** `any()`만 세서,
      원래 있던 위반을 "주입 검출"로 계상했다.

이 v3가 하는 것
  · 세션별로 키를 분리한다(덮어쓰기 제거)
  · 시행 판정을 **비율 상한 30%** 규칙으로 계산한다
  · 주입 검출을 **같은 창의 주입 전 위반 대비 증가분**으로 계산한다(net)
  · 손가락 끝(landmark 8)이 속한 분절이 **(7,8) 하나뿐**이므로
    I1/I2/I4는 "2개 이상 동시 위반" 조건에서 **원리적으로 검출 불가**임을
    **강체(rigid) 합성손**으로 확인한다(떨림 배제).

정직: 환자 원영상 오류 라벨이 없으므로 여기서 재는 것은 "미주입 자료의 위반률"이며
      참된 오경보율이 아니다. I1/I2/I4는 손끝 한 점만 바꾼다(손 전체 소실이 아니다).

출력: experiments/results/v15_failure_injection_v3.json
"""
from __future__ import annotations
import glob, io, json, math, os
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from failure_injection import (  # noqa: E402  (정의·로더 재사용, 원 파일 수정 없음)
    ROOT, OUT as V2OUT, TOL, MIN_AGREE, REST_S, SEGMENTS, FINGER_OF, FLEX_DEFS, FNAMES,
    load_windows, per_frame, rule_current, rule_B, fit_kappa, inject)

OUT3 = "experiments/results/v15_failure_injection_v3.json"
CAP = 0.30  # 계획서 §8.2 잠정 상한


def flag_rate(flags, L):
    """검사 가능한 프레임 = 분절을 계산할 수 있는 프레임. 그 중 위반 비율."""
    usable = np.isfinite(L).any(axis=1)
    n = int(usable.sum())
    if n == 0:
        return None, 0
    return float((flags & usable).sum()) / n, n


def main():
    sessions = [d for d in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, d))]
    groups = {}
    for d in sessions:
        m = glob.glob(os.path.join(ROOT, d, "*_metadata.json"))
        g = "Healthy"
        if m:
            j = json.load(io.open(m[0], encoding="utf-8-sig"))
            if (j.get("subject") or {}).get("group") == "Patient":
                g = "Patient"
        groups[d] = g

    res = {"provenance": {
        "fixed_from_v2": ["O1 세션 키 분리", "O2 비율상한 30% 규칙", "O3 주입전 위반 차감"],
        "tol": TOL, "min_agree": MIN_AGREE, "cap": CAP,
        "caveat": "오류 라벨 없음 → 미주입 위반률이며 참 오경보율이 아님. I1/I2/I4는 손끝 한 점만 변경."},
        "per_session": {}, "injection_net": {}, "rigid_hand_check": {}}

    # ── (1) 세션별 미주입 위반률 + 30% 상한 탈락 수 ───────────────────────────
    print("=" * 108)
    print("(1) 미주입 자료의 위반률 — 세션별 보존 (v2는 환자 2세션이 덮여 있었음)")
    print("=" * 108)
    print("%-40s %-6s %5s | %8s %8s | %6s %6s" % ("세션", "손", "창", "현행률", "B률", "현행탈락", "B탈락"))
    tot = {"cur": 0, "B": 0, "n": 0}
    for d in sessions:
        for hand in ("Left", "Right"):
            wins = load_windows(os.path.join(ROOT, d), hand)
            if not wins:
                continue
            others = []
            for (dd, hh) in [(x, y) for x in sessions for y in ("Left", "Right")]:
                if dd != d:
                    others += [per_frame(w["P"], w["t"])
                               for w in load_windows(os.path.join(ROOT, dd), hh)]
            kappa = fit_kappa(others)
            rc, rb, n = [], [], 0
            for w in wins:
                pf = per_frame(w["P"], w["t"])
                a, _ = flag_rate(rule_current(pf), pf["L"])
                b_, _ = flag_rate(rule_B(pf, kappa), pf["L"])
                if a is not None:
                    rc.append(a)
                if b_ is not None:
                    rb.append(b_)
                n += 1
            dc = sum(1 for x in rc if x > CAP)
            db = sum(1 for x in rb if x > CAP)
            tot["cur"] += dc
            tot["B"] += db
            tot["n"] += n
            res["per_session"]["%s||%s" % (d, hand)] = {
                "group": groups[d], "n": n,
                "cur_median_rate": float(np.median(rc)) if rc else None,
                "B_median_rate": float(np.median(rb)) if rb else None,
                "cur_reject_over_cap": dc, "B_reject_over_cap": db}
            print("%-40s %-6s %5d | %8.3f %8.3f | %6d %6d" % (
                d[:38], hand, n, np.median(rc) if rc else -1, np.median(rb) if rb else -1, dc, db))
    print("-" * 108)
    print("%-49s | %-25s | %6d %6d  (총 %d창)" % ("합계", "", tot["cur"], tot["B"], tot["n"]))

    # ── (2) 주입 검출: 주입 전 위반 대비 증가분 ──────────────────────────────
    print()
    print("=" * 108)
    print("(2) 주입 검출(net) — 같은 창의 주입 전 위반을 뺀 뒤, 검출 프레임이 늘었는가")
    print("=" * 108)
    rng = np.random.default_rng(20261002)
    print("%-26s %5s | %-13s %-13s" % ("집단|손|주입", "창", "현행(net검출)", "B(net검출)"))
    acc = {}
    for d in sessions:
        for hand in ("Left", "Right"):
            wins = load_windows(os.path.join(ROOT, d), hand)
            if not wins:
                continue
            others = []
            for (dd, hh) in [(x, y) for x in sessions for y in ("Left", "Right")]:
                if dd != d:
                    others += [per_frame(w["P"], w["t"])
                               for w in load_windows(os.path.join(ROOT, dd), hh)]
            kappa = fit_kappa(others)
            for kind in ("I1_jump", "I2_loss", "I3_scale", "I4_collapse"):
                nc = nb = 0
                for w in wins:
                    P, t = w["P"], w["t"]
                    base = per_frame(P, t)
                    bc = rule_current(base); bb = rule_B(base, kappa)
                    idx0 = max(1, int(0.35 * P.shape[0]))
                    Q, sl = inject(P, kind, idx0, 8, rng)
                    pf2 = per_frame(Q, t)
                    cc = rule_current(pf2); cb = rule_B(pf2, kappa)
                    # 주입 구간에서 '새로' 위반이 생긴 프레임 수
                    inc_c = int(np.sum(cc[sl] & ~bc[sl]))
                    inc_b = int(np.sum(cb[sl] & ~bb[sl]))
                    nc += int(inc_c > 0)
                    nb += int(inc_b > 0)
                k = "%s|%s|%s" % (groups[d], hand, kind)
                res["injection_net"]["%s||%s" % (d, k)] = {"n": len(wins), "cur": nc / len(wins), "B": nb / len(wins)}
                acc.setdefault(k, []).append((nc / len(wins), nb / len(wins), len(wins)))
    for k in sorted(acc):
        rows = acc[k]
        n = sum(r[2] for r in rows)
        c = sum(r[0] * r[2] for r in rows) / n
        b_ = sum(r[1] * r[2] for r in rows) / n
        print("%-26s %5d | %13.2f %13.2f" % (k, n, c, b_))

    # ── (3) 강체 합성손 검사: 손끝(8)은 (7,8) 한 분절에만 속한다 ────────────
    print()
    print("=" * 108)
    print("(3) 강체(rigid) 합성손 — 떨림을 완전히 제거하고 주입했을 때 검출되는가")
    print("=" * 108)
    d0 = sessions[0]
    w0 = load_windows(os.path.join(ROOT, d0), "Left")
    P0 = w0[0]["P"]
    mid = P0[P0.shape[0] // 2]
    N = 60
    t = np.arange(N) * 0.077
    rigid = np.tile(mid, (N, 1, 1))
    pf = per_frame(rigid, t)
    base_f = rule_current(pf)
    print("  주입 전 위반 프레임: %d / %d  (강체이므로 0이어야 정상)" % (base_f.sum(), N))
    res["rigid_hand_check"]["baseline_violation_frames"] = int(base_f.sum())
    for kind in ("I1_jump", "I2_loss", "I3_scale", "I4_collapse"):
        Q, sl = inject(rigid, kind, 20, 8, rng)
        pf2 = per_frame(Q, t)
        cc = rule_current(pf2)
        inc = int(np.sum(cc[sl] & ~base_f[sl]))
        res["rigid_hand_check"][kind] = {"detected_frames": inc, "of": 8}
        print("  %-12s 주입 8프레임 중 새 위반 프레임: %d" % (kind, inc))

    io.open(OUT3, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    print()
    print("JSON →", OUT3)


if __name__ == "__main__":
    main()
