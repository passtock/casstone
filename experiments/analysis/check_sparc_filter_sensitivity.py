# -*- coding: utf-8 -*-
"""SPARC 재검: 추가 저역통과 필터를 씌우면 반복성(MDC)이 좋아지는가?

배경: 앱(clock_v3)은 ① One-Euro 필터된 각도 ② 보수적 균일격자 ③ 추가 LP 없음 으로 SPARC를 낸다.
      실측 MDC는 69–102%(기준 ≤50%). "필터를 더 씌우면 살아나는가?"를 직접 확인한다.

방법: continuous_raw.csv에서 flex(=4손가락 PIP 평균)를 만들고,
      cutoff ∈ {none,4,3,2,1.5,1,0.7} Hz 의 Butterworth(zero-phase)를 추가로 적용한 뒤
      앱과 동일한 sparc() 정의로 계산 → 시행 간 MDC95/|mean| 를 손별로 비교.

작성 2026-09-30. 읽기 전용.
"""
import csv
import io
import math
import os
import sys
from collections import defaultdict

import numpy as np
from scipy.signal import butter, filtfilt

PIPS = ("Index_PIP", "Middle_PIP", "Ring_PIP", "Pinky_PIP")


def sparc(vel, times, fc=10.0, amplitude_threshold=0.05):
    """clock_v3와 동일 구현(충실 재현)."""
    try:
        t = np.asarray(times, float)
        speed = np.abs(np.asarray(vel, float))
        if len(t) < 20 or speed.shape != t.shape or not np.isfinite(speed).all():
            return None
        dt = np.diff(t)
        if not np.allclose(dt, dt[0], rtol=1e-4, atol=1e-9):
            return None
        if np.max(speed) < 1e-4 or fc <= 0:
            return None
        nfft = 2 ** (int(np.ceil(np.log2(len(speed)))) + 4)
        spectrum = np.abs(np.fft.rfft(speed, n=nfft))
        spectrum /= np.max(spectrum)
        freq = np.fft.rfftfreq(nfft, d=float(dt[0]))
        eligible = np.flatnonzero((freq <= min(fc, 0.5 / dt[0])) & (spectrum >= amplitude_threshold))
        if len(eligible) < 2 or eligible[-1] < 2:
            return None
        end = int(eligible[-1])
        f, m = freq[:end + 1], spectrum[:end + 1]
        return float(-np.sum(np.sqrt((np.diff(f) / f[-1]) ** 2 + np.diff(m) ** 2)))
    except (ValueError, TypeError, FloatingPointError):
        return None


def sparc_like_app(t, a, extra_cutoff=None):
    """앱과 동일한 전처리(보수적 균일격자) + 선택적 추가 LP."""
    t = np.asarray(t, float)
    a = np.asarray(a, float)
    ok = np.isfinite(t) & np.isfinite(a)
    t, a = t[ok], a[ok]
    if len(t) < 20 or np.any(np.diff(t) <= 0):
        return None, None
    span = float(t[-1] - t[0])
    n = int(np.floor(span / np.max(np.diff(t)))) + 1
    if n < 20:
        return None, None
    grid = np.linspace(0.0, span, n)
    ang = np.interp(grid, t - t[0], a)
    fs = float((n - 1) / span)
    if extra_cutoff is not None:
        wn = float(extra_cutoff) / (fs / 2.0)
        if wn >= 1.0 or wn <= 0:
            return None, fs
        b, aa = butter(2, wn, btype="low")
        if len(ang) > 3 * 3:
            ang = filtfilt(b, aa, ang)
    speed = np.abs(np.gradient(ang, grid))
    return sparc(speed, grid, fc=min(10.0, fs / 2.0)), fs


def mdc_ratio(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return None
    m = float(np.mean(v))
    if abs(m) < 1e-9:
        return None
    return 1.96 * math.sqrt(2) * float(np.std(v, ddof=1)) / abs(m) * 100.0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sess = sys.argv[1].rstrip("/\\")
    fs_ = [p for p in os.listdir(sess) if p.endswith("_continuous_raw.csv")]
    if not fs_:
        print("continuous_raw.csv 없음")
        return 1
    path = os.path.join(sess, fs_[0])

    recs = defaultdict(lambda: {"t": [], "raw": [], "filt": []})
    with io.open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            key = (r.get("Trial"), r.get("hand"))
            try:
                t = float(r["time_s"])
            except Exception:
                continue
            def av(col):
                vals = []
                for j in PIPS:
                    try:
                        vals.append(float(r[f"{j}_{col}"]))
                    except Exception:
                        pass
                return float(np.mean(vals)) if len(vals) == len(PIPS) else None
            recs[key]["t"].append(t)
            recs[key]["raw"].append(av("raw"))
            recs[key]["filt"].append(av("filt"))

    print("=" * 92)
    print("세션: %s" % os.path.basename(sess))
    print("=" * 92)
    print("\n[0] 격자 확인 (앱과 동일: n=floor(span/max dt)+1)")
    for key in sorted(recs)[:2]:
        d = recs[key]
        t = np.asarray(d["t"], float)
        if len(t) >= 20 and np.all(np.diff(t) > 0):
            span = t[-1] - t[0]
            n = int(np.floor(span / np.max(np.diff(t)))) + 1
            print("  %s: 원프레임 %d (mean dt %.4fs) → 보수격자 n=%d, fs≈%.2f Hz, Nyquist %.2f Hz"
                  % (key, len(t), float(np.mean(np.diff(t))), n, (n - 1) / span, ((n - 1) / span) / 2))

    srcs = (("filt(앱과 동일)", "filt"), ("raw(원신호)", "raw"))
    cuts = (None, 4.0, 3.0, 2.0, 1.5, 1.0, 0.7)
    for src_label, sk in srcs:
        print("\n[%s] 추가 LP cutoff별 SPARC 반복성(MDC95/|mean| %%)" % src_label)
        hdr = "%-10s" % "cutoff"
        for h in ("Left", "Right"):
            hdr += "%12s" % h
        hdr += "%10s" % "n(좌/우)"
        print(hdr)
        for c in cuts:
            row = "%-10s" % ("none" if c is None else "%.1f Hz" % c)
            n_by = {}
            for h in ("Left", "Right"):
                vals = []
                for key, d in recs.items():
                    if key[1] != h:
                        continue
                    v, _ = sparc_like_app(d["t"], d[sk], extra_cutoff=c)
                    if v is not None:
                        vals.append(v)
                n_by[h] = len(vals)
                r = mdc_ratio(vals)
                row += "%12s" % (("%.1f" % r) if r is not None else "-")
            row += "%10s" % ("%d/%d" % (n_by["Left"], n_by["Right"]))
            print(row)
    print("\n⚠️ 필터를 씌우면 SPARC의 정의상 '측정 대상(고주파 거침)'을 깎아낸다. 해석 주의.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
