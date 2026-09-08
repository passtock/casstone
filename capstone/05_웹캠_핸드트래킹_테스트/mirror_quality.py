"""Read-only quality diagnostics; never relabel hands or repair measurements."""
import numpy as np


def assess_hand_identity(previous, current, timestamp, *, previous_timestamp=None,
                         max_gap=0.75, ambiguity_margin=0.03):
    """Compare two labelled wrist pairs in unmirrored normalized image XY.

    Costs are sums of Euclidean image distances, not physical distances.
    A flag is only a suspicion: crossing hands can produce the same result.
    Callers must retain raw labels and update previous on every actual frame,
    including frames without hands. No continuity is inferred across absence.
    """
    result = dict(status='not_assessed', flags={}, direct_cost=None, swapped_cost=None)
    if previous_timestamp is None or not np.isfinite([timestamp, previous_timestamp]).all():
        return result
    if not 0 < timestamp - previous_timestamp <= max_gap:
        result['status'] = 'time_gap'
        return result
    labels = ('Left', 'Right')
    if set(previous) != set(labels) or set(current) != set(labels):
        result['status'] = 'insufficient_pair'
        return result
    p = np.asarray([previous[k] for k in labels], dtype=float)
    c = np.asarray([current[k] for k in labels], dtype=float)
    if p.shape != (2, 2) or c.shape != (2, 2) or not np.isfinite([p, c]).all():
        result['status'] = 'invalid_wrist'
        return result
    direct = float(np.linalg.norm(c-p, axis=1).sum())
    swapped = float(np.linalg.norm(c[::-1]-p, axis=1).sum())
    status = ('ambiguous' if abs(direct-swapped) <= ambiguity_margin else
              'possible_label_swap' if swapped < direct else 'consistent')
    result.update(status=status, direct_cost=direct, swapped_cost=swapped)
    if status != 'consistent':
        result['flags'] = {k: status for k in labels}
    return result


def sparc_segment(times, speed, *, max_gap=0.25, min_samples=10,
                  min_duration=0.5, padlevel=4, fc=10.0, amp_th=0.05):
    """Exploratory SPARC for ONE preselected contiguous discrete movement.

    Seconds and nonnegative speed of one consistent unit are required.
    Linear resampling uses the original sample count and both endpoints.
    Missing, unordered, negative or gapped input is rejected, never filled.
    Caller owns phase selection and derivative calculation. No clinical cutoff.
    See sparc_reference.md for algorithm provenance and analysis limitations.
    """
    t, v = np.asarray(times, dtype=float), np.asarray(speed, dtype=float)
    out = dict(value=None, reason='invalid_shape', n_samples=int(t.size),
               fs=None, cutoff_hz=None, duration_s=None)
    if t.ndim != 1 or v.shape != t.shape:
        return out
    if (min_samples < 2 or min_duration <= 0 or max_gap <= 0 or fc <= 0
            or not 0 < amp_th < 1 or not isinstance(padlevel, int) or not 0 <= padlevel <= 10):
        out['reason'] = 'invalid_config'
        return out
    if len(t) < min_samples:
        out['reason'] = 'insufficient_samples'
        return out
    if not np.isfinite(t).all() or not np.isfinite(v).all():
        out['reason'] = 'missing_or_nonfinite'
        return out
    dt = np.diff(t)
    if np.any(dt <= 0):
        out['reason'] = 'nonincreasing_timestamps'
        return out
    out['duration_s'] = float(t[-1]-t[0])
    if np.any(dt > max_gap):
        out['reason'] = 'tracking_gap'
        return out
    if out['duration_s'] < min_duration:
        out['reason'] = 'insufficient_duration'
        return out
    if np.any(v < 0):
        out['reason'] = 'negative_speed'
        return out
    if not np.any(v > 0):
        out['reason'] = 'zero_speed'
        return out
    fs = (len(t)-1)/out['duration_s']
    out['fs'] = float(fs)
    uniform_v = np.interp(np.linspace(t[0], t[-1], len(t)), t, v)
    nfft = 2 ** (int(np.ceil(np.log2(len(t)))) + padlevel)
    spectrum = np.abs(np.fft.rfft(uniform_v, n=nfft))
    spectrum /= spectrum.max()
    freq = np.fft.rfftfreq(nfft, d=1/fs)
    eligible = np.flatnonzero((freq <= min(fc, fs/2)) & (spectrum >= amp_th))
    if len(eligible) < 2 or eligible[-1] == 0:
        out['reason'] = 'insufficient_spectral_band'
        return out
    stop = int(eligible[-1]) + 1
    f, s = freq[:stop], spectrum[:stop]
    out.update(value=float(-np.sqrt((np.diff(f)/(f[-1]-f[0]))**2 + np.diff(s)**2).sum()),
               reason='ok', cutoff_hz=float(f[-1]))
    return out


def gap_plot_arrays(times, values, max_gap=0.25):
    """Insert NaN separators for absent/nonmonotonic time; preserve samples."""
    if len(times) != len(values):
        raise ValueError('times and values must have equal length')
    x, y = [], []
    previous = None
    for t, v in zip(times, values):
        t = float(t)
        if previous is not None and (not np.isfinite([t, previous]).all()
                                     or not 0 < t-previous <= max_gap):
            x.append(np.nan)
            y.append(np.nan)
        x.append(t)
        y.append(np.nan if v is None else float(v))
        previous = t
    return np.asarray(x), np.asarray(y)
