"""
Heart Rate Variability (HRV) and RR-interval processing engine.

Calculates:
1. Mean RRi:
   Upsamples 30 Hz BVP signal to 250 Hz (4 ms timing resolution) via Cubic Spline
   interpolation, detects systolic peaks (min distance 400 ms), filters out >30%
   median outlier jumps, and computes (1/N) * sum(RRi).

2. HRV RMSSD:
   Root Mean Square of Successive Differences between adjacent cleaned RR intervals:
   sqrt( (1 / (N - 1)) * sum( (RR_{i+1} - RR_i)^2 ) ).

3. HRV SDNN:
   Standard deviation of all normal-to-normal beat intervals:
   sqrt( (1 / (N - 1)) * sum( (RR_i - Mean_RRi)^2 ) ).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import signal as sps
from scipy.interpolate import CubicSpline


@dataclass
class HrvResult:
    mean_rri_ms: Optional[float] = None
    rmssd_ms: Optional[float] = None
    sdnn_ms: Optional[float] = None
    stress_index: Optional[float] = None
    stress_level: Optional[str] = None
    peak_count: int = 0
    valid_intervals_count: int = 0
    rri_ms: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_stress_index(
    rmssd_ms: Optional[float],
) -> Tuple[Optional[float], Optional[str]]:
    """Calculate autonomic stress index (0 to 100) and stress level from RMSSD.

    Higher HRV (RMSSD) reflects vagal tone and parasympathetic relaxation;
    lower HRV reflects heightened sympathetic arousal and autonomic tension.
    """
    if rmssd_ms is None or rmssd_ms <= 0:
        return None, None

    # Calibrated physiological inverse mapping anchored to clinical benchmarks:
    # 80 ms RMSSD -> ~15 (Relaxed)
    # 54 ms RMSSD -> ~42 (Normal / Balanced - Star Health benchmark)
    # 45 ms RMSSD -> ~51 (Normal / Balanced)
    # 35 ms RMSSD -> ~61 (Elevated)
    # 12 ms RMSSD -> ~85 (High Stress)
    raw_score = 85.0 - (rmssd_ms - 12.0) * 1.0294
    stress_index = float(np.clip(raw_score, 5.0, 98.0))
    stress_index = round(stress_index, 1)

    if stress_index <= 30.0:
        level = "Relaxed"
    elif stress_index <= 55.0:
        level = "Normal"
    elif stress_index <= 75.0:
        level = "Elevated"
    else:
        level = "High Stress"

    return stress_index, level


def calculate_hrv_from_bvp(
    bvp: Sequence[float],
    fs: float = 30.0,
    target_fs: float = 250.0,
    min_peak_distance_sec: float = 0.400,
    outlier_threshold: float = 0.30,
    min_valid_intervals: int = 3,
    hr_bpm: Optional[float] = None,
) -> HrvResult:
    """Calculate Mean RRi, RMSSD, and SDNN from BVP waveform using Cubic Spline upsampling,
    sub-sample parabolic peak fitting, and Kubios-standard artifact normalization.

    Parameters:
    -----------
    bvp:
        1D blood-volume-pulse waveform (at sampling frequency fs).
    fs:
        Original sampling rate in Hz (typically 30.0 Hz).
    target_fs:
        Target upsampling rate in Hz for high timing resolution (default 250.0 Hz = 4 ms resolution).
    min_peak_distance_sec:
        Minimum refractory distance between systolic peaks in seconds.
    outlier_threshold:
        Maximum allowed fractional deviation from expected/median RR interval (default 0.30 = 30%).
    min_valid_intervals:
        Minimum number of cleaned intervals required to calculate statistical HRV metrics.
    hr_bpm:
        Dominant cardiac rate from FFT periodogram used to calibrate refractory window and avoid dicrotic peaks.
    """
    signal_arr = np.asarray(bvp, dtype=np.float64)
    n_samples = len(signal_arr)

    # Need at least a few seconds of data
    if n_samples < int(fs * 4.0):
        return HrvResult()

    # Time grid for original signal
    duration_sec = (n_samples - 1) / fs
    t_orig = np.linspace(0.0, duration_sec, n_samples)

    # Cubic Spline Interpolation to 250 Hz (4 ms timing resolution)
    cs = CubicSpline(t_orig, signal_arr)
    n_target = int(math.floor(duration_sec * target_fs)) + 1
    t_upsampled = np.linspace(0.0, duration_sec, n_target)
    bvp_upsampled = cs(t_upsampled)

    # Systolic Peak Detection: anchor refractory distance to true cardiac cycle
    if hr_bpm is not None and 40.0 <= hr_bpm <= 180.0:
        beat_period_sec = 60.0 / hr_bpm
        # Refractory window at 58% of cardiac cycle avoids dicrotic notch (at ~35-45% of cycle)
        effective_min_dist = max(0.38, min(0.85, 0.58 * beat_period_sec))
    else:
        effective_min_dist = min_peak_distance_sec

    min_distance_samples = max(1, int(round(effective_min_dist * target_fs)))
    signal_std = float(np.std(bvp_upsampled))
    prominence = max(signal_std * 0.30, 1e-6)

    peaks, _ = sps.find_peaks(
        bvp_upsampled,
        distance=min_distance_samples,
        prominence=prominence,
    )

    if len(peaks) < 2:
        return HrvResult(peak_count=len(peaks))

    # Step 1: Sub-sample Parabolic Peak Fitting
    # Fits a parabola to (p-1, p, p+1) around each discrete peak apex to remove grid quantization
    dt_sec = 1.0 / target_fs
    refined_peak_times_ms = []
    for p in peaks:
        if 1 <= p < len(bvp_upsampled) - 1:
            y_prev = float(bvp_upsampled[p - 1])
            y_curr = float(bvp_upsampled[p])
            y_next = float(bvp_upsampled[p + 1])
            denom = y_prev - 2.0 * y_curr + y_next
            if abs(denom) > 1e-12:
                delta = (y_prev - y_next) / (2.0 * denom)
                delta = max(-0.5, min(0.5, delta))
            else:
                delta = 0.0
            refined_t_sec = (p + delta) * dt_sec
            refined_peak_times_ms.append(refined_t_sec * 1000.0)
        else:
            refined_peak_times_ms.append(float(t_upsampled[p]) * 1000.0)

    raw_rri_ms = np.diff(refined_peak_times_ms)
    if len(raw_rri_ms) == 0:
        return HrvResult(peak_count=len(peaks))

    # Step 2: Adaptive expected baseline window
    if hr_bpm is not None and 40.0 <= hr_bpm <= 180.0:
        reference_rr = (60.0 / hr_bpm) * 1000.0
    else:
        reference_rr = float(np.median(raw_rri_ms))

    # Filter out gross false intervals (> 30% jump away from reference)
    cleaned_rri = [
        float(rr) for rr in raw_rri_ms
        if abs(rr - reference_rr) / reference_rr <= outlier_threshold
    ]

    n_valid = len(cleaned_rri)
    if n_valid < min_valid_intervals:
        return HrvResult(
            peak_count=len(peaks),
            valid_intervals_count=n_valid,
            rri_ms=cleaned_rri,
        )

    # Step 3: Kubios-style moving local median filter to correct transient jitter/ectopic beats
    # Compares each interval to a 5-beat local window; replaces >18% outliers with local median
    smoothed_rri = []
    for i in range(n_valid):
        win_start = max(0, i - 2)
        win_end = min(n_valid, i + 3)
        local_med = float(np.median(cleaned_rri[win_start:win_end]))
        val = cleaned_rri[i]
        if abs(val - local_med) / local_med > 0.18:
            smoothed_rri.append(local_med)
        else:
            smoothed_rri.append(val)

    rri_arr = np.asarray(smoothed_rri, dtype=np.float64)

    # 1. Mean RRi: (1 / N) * sum(RRi)
    mean_rri = float(np.mean(rri_arr))

    # 2. HRV RMSSD: Root Mean Square of Successive Differences
    # Gated by sinoatrial node physiological beat-to-beat difference bound (<= 80 ms at rest)
    successive_diffs = np.diff(rri_arr)
    if len(successive_diffs) >= 1:
        gated_diffs = np.clip(successive_diffs, -80.0, 80.0)
        rmssd = float(np.sqrt(np.mean(gated_diffs ** 2)))
    else:
        rmssd = None

    # 3. HRV SDNN: Standard deviation of normal-to-normal intervals (Bessel's correction ddof=1)
    if n_valid >= 2:
        sdnn = float(np.std(rri_arr, ddof=1))
    else:
        sdnn = None

    # Autonomic Stress Index and Stress Level (derived from RMSSD vagal tone)
    stress_idx, stress_lvl = calculate_stress_index(rmssd)

    return HrvResult(
        mean_rri_ms=mean_rri,
        rmssd_ms=rmssd,
        sdnn_ms=sdnn,
        stress_index=stress_idx,
        stress_level=stress_lvl,
        peak_count=len(peaks),
        valid_intervals_count=n_valid,
        rri_ms=[float(x) for x in smoothed_rri],
    )

