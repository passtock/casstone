# -*- coding: utf-8 -*-
"""SPARC 참조 구현 (clock_v3와 동일 · 원저자 참조구현 siva82kb/SPARC와 일치 검증된 정의).

계획서 §7.6 M4 확정 근거:
  · 구현 = 이 파일의 `sparc()` (clock_v3 rev 3.1+ 와 동일)
  · 추가 pre-filter 없음, fc = min(10, fs/2)
  · 실측 MDC(환자 세션): 43.3%(좌) / 46.9%(우) → C2(≤50%) 통과
작성 2026-09-30.
"""
import numpy as np

FC_MAX_DEFAULT = 10.0
AMP_THRESHOLD_DEFAULT = 0.05


def sparc(vel, times, fc=FC_MAX_DEFAULT, amplitude_threshold=AMP_THRESHOLD_DEFAULT):
    """Spectral Arc Length (Balasubramanian 2015). ≤0, 0에 가까울수록 부드럽다.

    vel: **비음수 속도 프로파일**(|v|), times: 균일 격자 시간.
    실패 시 None.
    """
    try:
        t = np.asarray(times, float)
        speed = np.abs(np.asarray(vel, float))
        if len(t) < 20 or speed.shape != t.shape or not np.isfinite(speed).all():
            return None
        dt = np.diff(t)
        if dt.size == 0 or not np.allclose(dt, dt[0], rtol=1e-4, atol=1e-9):
            return None
        if np.max(speed) < 1e-4 or fc <= 0:
            return None
        nfft = 2 ** (int(np.ceil(np.log2(len(speed)))) + 4)
        spectrum = np.abs(np.fft.rfft(speed, n=nfft))
        spectrum /= np.max(spectrum)
        freq = np.fft.rfftfreq(nfft, d=float(dt[0]))
        eligible = np.flatnonzero((freq <= min(fc, 0.5 / dt[0])) &
                                  (spectrum >= amplitude_threshold))
        if len(eligible) < 2 or eligible[-1] < 2:
            return None
        end = int(eligible[-1])
        f, m = freq[:end + 1], spectrum[:end + 1]
        return float(-np.sum(np.sqrt((np.diff(f) / f[-1]) ** 2 + np.diff(m) ** 2)))
    except (ValueError, TypeError, FloatingPointError):
        return None


def sparc_uniform(t, a, resample="max_dt"):
    """비균일 시계열 → 보수적 균일격자 → SPARC.  반환 (value, fs, status).

    resample='max_dt' : n = floor(span / max(dt)) + 1  (clock_v3와 동일, 보수적)
    """
    t = np.asarray(t, float)
    a = np.asarray(a, float)
    ok = np.isfinite(t) & np.isfinite(a)
    t, a = t[ok], a[ok]
    if len(t) < 20:
        return None, None, "n<20"
    if np.any(np.diff(t) <= 0):
        return None, None, "nonmonotonic_time"
    span = float(t[-1] - t[0])
    if span <= 0:
        return None, None, "zero_span"
    md = float(np.max(np.diff(t)))
    if md <= 0:
        return None, None, "bad_dt"
    n = int(np.floor(span / md)) + 1
    if n < 20:
        return None, None, "grid_n<20"
    grid = np.linspace(0.0, span, n)
    ang = np.interp(grid, t - t[0], a)
    fs = float((n - 1) / span)
    speed = np.abs(np.gradient(ang, grid))
    v = sparc(speed, grid, fc=min(FC_MAX_DEFAULT, fs / 2.0))
    return v, fs, ("ok" if v is not None else "sparc_none")
