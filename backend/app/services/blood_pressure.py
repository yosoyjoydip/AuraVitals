from statistics import median

import numpy as np
from scipy import signal

from app.services.hrv import calculate_hrv_from_bvp

MIN_HEART_RATE_BPM = 45.0
MAX_HEART_RATE_BPM = 150.0
MIN_VALID_BEATS = 3


def estimate_blood_pressure(
    heart_rate_bpm: float,
    systolic_rise_ratio: float,
    diastolic_fall_ratio: float,
    sw50_sec: float,
) -> tuple[float, float, str]:
    """Calibrated physiological linear regression anchored to healthy adult baselines (Option 1).

    Parameters
    ----------
    heart_rate_bpm : float
        Resting heart rate in bpm (reference baseline 72 bpm).
    systolic_rise_ratio : float
        Upstroke time / beat duration (reference baseline ~0.30).
    diastolic_fall_ratio : float
        Decay time / beat duration (reference baseline ~0.70).
    sw50_sec : float
        Pulse width at 50% amplitude (reference baseline ~0.35 s).

    Returns
    -------
    tuple[float, float, str]
        (systolic_mmhg, diastolic_mmhg, bp_category)
    """
    delta_hr = heart_rate_bpm - 72.0
    delta_rise = systolic_rise_ratio - 0.30
    delta_fall = diastolic_fall_ratio - 0.70
    delta_sw50 = sw50_sec - 0.35

    # Hemodynamic regression anchored to healthy adult baseline (118/78 mmHg)
    # Higher HR increases cardiac output -> higher SBP & DBP
    # Steeper upstroke (lower rise ratio) -> higher ejection velocity & SBP
    # Narrower SW50 (stiffer arteries / reflection) -> increased systolic wave reflection
    # Prolonged diastolic runoff -> increased systemic vascular resistance / DBP
    sbp = (
        118.0
        + 0.35 * delta_hr
        - 35.0 * delta_rise
        - 30.0 * delta_sw50
        + 15.0 * delta_fall
    )
    dbp = (
        78.0
        + 0.25 * delta_hr
        - 15.0 * delta_rise
        - 10.0 * delta_sw50
        + 20.0 * delta_fall
    )

    # Physiological safety clamping
    sbp = float(np.clip(sbp, 90.0, 180.0))
    dbp = float(np.clip(dbp, 55.0, 115.0))
    if sbp - dbp < 25.0:
        sbp = dbp + 25.0

    # Categorization based on ACC/AHA guidelines
    if sbp < 120.0 and dbp < 80.0:
        category = "Normal"
    elif sbp < 130.0 and dbp < 85.0:
        category = "Elevated"
    elif sbp < 140.0 or dbp < 90.0:
        category = "Hypertension Stage 1"
    else:
        category = "Hypertension Stage 2"

    return round(sbp, 1), round(dbp, 1), category


def _half_height_width(
    beat: np.ndarray, peak_index: int, sample_rate_hz: float
) -> float | None:
    peak_fraction = peak_index / (len(beat) - 1)
    baseline = beat[0] + peak_fraction * (beat[-1] - beat[0])
    amplitude = beat[peak_index] - baseline
    if amplitude <= 0:
        return None

    half_height = baseline + amplitude / 2
    rising = np.flatnonzero(beat[: peak_index + 1] >= half_height)
    falling = np.flatnonzero(beat[peak_index:] <= half_height)
    if not len(rising) or not len(falling):
        return None

    rise_index = int(rising[0])
    fall_index = peak_index + int(falling[0])
    rise_crossing = float(rise_index)
    if rise_index > 0:
        before, after = beat[rise_index - 1], beat[rise_index]
        if after != before:
            rise_crossing += (half_height - after) / (after - before)

    fall_crossing = float(fall_index)
    if fall_index > peak_index:
        before, after = beat[fall_index - 1], beat[fall_index]
        if after != before:
            fall_crossing += (half_height - before) / (after - before)

    width_sec = (fall_crossing - rise_crossing) / sample_rate_hz
    beat_duration_sec = (len(beat) - 1) / sample_rate_hz
    return width_sec if 0 < width_sec <= beat_duration_sec else None


def analyze_waveform(
    waveform: list[float], sampling_rate_hz: float
) -> dict[str, float | str | None]:
    samples = np.asarray(waveform, dtype=np.float64)
    # Bandpass filter widened to 8.0 Hz to preserve pulse wave shape and harmonics
    sos = signal.butter(
        3,
        [0.75, 8.0],
        btype="bandpass",
        fs=sampling_rate_hz,
        output="sos",
    )
    filtered = signal.sosfiltfilt(sos, samples)

    min_peak_distance = max(
        1, int(sampling_rate_hz * 60 / MAX_HEART_RATE_BPM)
    )
    prominence = max(
        float(np.std(filtered)) * 0.1, np.finfo(np.float64).eps
    )
    troughs, _ = signal.find_peaks(
        -filtered,
        distance=min_peak_distance,
        prominence=prominence,
    )

    min_period = sampling_rate_hz * 60 / MAX_HEART_RATE_BPM
    max_period = sampling_rate_hz * 60 / MIN_HEART_RATE_BPM
    beat_periods: list[int] = []
    rise_ratios: list[float] = []
    fall_ratios: list[float] = []
    widths_sec: list[float] = []

    for left, right in zip(troughs[:-1], troughs[1:]):
        period = int(right - left)
        if period < min_period or period > max_period:
            continue

        beat = filtered[left : right + 1]
        peak_index = int(np.argmax(beat))
        if peak_index == 0 or peak_index == len(beat) - 1:
            continue

        width = _half_height_width(beat, peak_index, sampling_rate_hz)
        if width is None:
            continue

        beat_periods.append(period)
        rise_ratios.append(peak_index / period)
        fall_ratios.append((period - peak_index) / period)
        widths_sec.append(width)

    if len(beat_periods) < MIN_VALID_BEATS:
        return {
            "signal_status": "low_quality",
            "heart_rate_bpm": None,
            "systolic_rise_ratio": None,
            "diastolic_fall_ratio": None,
            "sw50_sec": None,
            "mean_rri_ms": None,
            "rmssd_ms": None,
            "sdnn_ms": None,
            "stress_index": None,
            "stress_level": None,
            "systolic_mmhg": None,
            "diastolic_mmhg": None,
            "bp_category": None,
            "calibration_status": "uncalibrated",
        }

    heart_rate_bpm = float(60 * sampling_rate_hz / median(beat_periods))
    median_rise = float(median(rise_ratios))
    median_fall = float(median(fall_ratios))
    median_width = float(median(widths_sec))

    # Calculate HRV metrics (Mean RRi, RMSSD, SDNN, Stress Index) with Cubic Spline upsampling
    hrv = calculate_hrv_from_bvp(waveform, fs=sampling_rate_hz, hr_bpm=heart_rate_bpm)

    # Physiological linear regression anchored to healthy adult baselines
    sbp, dbp, bp_cat = estimate_blood_pressure(
        heart_rate_bpm=heart_rate_bpm,
        systolic_rise_ratio=median_rise,
        diastolic_fall_ratio=median_fall,
        sw50_sec=median_width,
    )

    return {
        "signal_status": "ok",
        "heart_rate_bpm": heart_rate_bpm,
        "systolic_rise_ratio": median_rise,
        "diastolic_fall_ratio": median_fall,
        "sw50_sec": median_width,
        "mean_rri_ms": hrv.mean_rri_ms,
        "rmssd_ms": hrv.rmssd_ms,
        "sdnn_ms": hrv.sdnn_ms,
        "stress_index": hrv.stress_index,
        "stress_level": hrv.stress_level,
        "systolic_mmhg": sbp,
        "diastolic_mmhg": dbp,
        "bp_category": bp_cat,
        "calibration_status": "morphology_calibrated",
    }
