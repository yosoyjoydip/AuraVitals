"""
rPPG vital-sign engine (Tier 1), rPPG-Toolbox POS.

Recovers blood-volume-pulse (BVP) from timestamped RGB traces captured on-device
from facial ROIs (forehead + cheeks) and estimates heart rate, respiration,
and pulse morphology.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import signal as sps
from scipy.signal import detrend as sp_detrend, hilbert
from scipy.sparse import spdiags

from app.services.blood_pressure import analyze_waveform
from app.services.hrv import calculate_hrv_from_bvp
from app.services.spo2 import calculate_spo2_from_rgb

RPPG = {
    "FPS_TARGET": 30.0,        # uniform resample rate (Hz)
    "HR_MIN_HZ": 0.75,         # 45 bpm
    "HR_MAX_HZ": 2.5,          # 150 bpm
    "RESP_MIN_HZ": 0.1,        # 6 breaths/min
    "RESP_MAX_HZ": 0.5,        # 30 breaths/min
    "POS_WIN_SEC": 1.6,        # POS sliding window (Wang et al. 2017)
    "MIN_DURATION_SEC": 12.0,  # minimum duration required
    "SQI_MIN": 0.25,           # cardiac spectral SNR threshold
    "RESP_SQI_MIN": 0.25,      # respiratory spectral SNR threshold
}


@dataclass
class VitalResult:
    status: str                          # 'ok' | 'too_short' | 'low_quality' | 'no_signal'
    hr_bpm: Optional[float]              # None unless status == 'ok'
    hr_sqi: float                        # 0..1 spectral SNR for the cardiac peak
    resp_bpm: Optional[float]
    resp_sqi: float
    duration_sec: float
    fps_effective: float                 # measured mean sampling rate of raw trace
    samples: int
    prq: Optional[float] = None          # Pulse-Respiration Quotient: HR / Resp
    stress_index: Optional[float] = None # Autonomic stress score 0-100
    stress_level: Optional[str] = None   # Relaxed, Normal, Elevated, High Stress
    stress_level_ps: Optional[str] = None # e.g. '1 ps', '2 ps'
    stress_index_ms: Optional[float] = None # Time-domain stress index in ms (~75 ms)
    sns_zone: Optional[int] = None       # Sympathetic tone zone (1 to 5)
    pns_zone: Optional[int] = None       # Parasympathetic recovery zone (1 to 5)
    lf_hf_ratio: Optional[float] = None  # Sympathovagal LF/HF ratio
    bvp: Optional[List[float]] = None    # recovered blood-volume-pulse waveform
    best_roi: Optional[str] = None
    morphology: Optional[Dict[str, Optional[float]]] = None
    hrv: Optional[Dict[str, Any]] = None
    systolic_mmhg: Optional[float] = None
    diastolic_mmhg: Optional[float] = None
    bp_category: Optional[str] = None
    spo2_percent: Optional[float] = None
    spo2_r_ratio: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _detrend(input_signal: np.ndarray, lambda_value: float = 100.0) -> np.ndarray:
    """Smoothness-prior detrend (Tarvainen et al. 2002)."""
    signal_length = input_signal.shape[0]
    if signal_length < 3:
        return input_signal
    identity_matrix = np.identity(signal_length)
    ones = np.ones(signal_length)
    minus_twos = -2.0 * np.ones(signal_length)
    diags_data = np.array([ones, minus_twos, ones])
    diags_index = np.array([0, 1, 2])
    d_mat = spdiags(diags_data, diags_index, (signal_length - 2), signal_length).toarray()
    detrended = np.dot(
        (identity_matrix - np.linalg.inv(identity_matrix + (lambda_value ** 2) * np.dot(d_mat.T, d_mat))),
        input_signal,
    )
    return detrended


def _next_power_of_2(x: int) -> int:
    return 1 if x == 0 else 2 ** (x - 1).bit_length()


def pos_wang(rgb: np.ndarray, fs: float) -> np.ndarray:
    """POS algorithm (Wang et al. 2017).

    Takes pre-computed (N, 3) RGB trace and sampling frequency fs.
    """
    sample_count = rgb.shape[0]
    pulse_accumulator = np.zeros(sample_count)
    window_length = math.ceil(RPPG["POS_WIN_SEC"] * fs)

    for n in range(sample_count):
        m = n - window_length
        if m >= 0:
            win = rgb[m:n, :]
            mu = np.mean(win, axis=0)
            mu[mu == 0] = 1e-8
            normalized_c = (win / mu).T  # 3 x window_length
            s = np.array([[0.0, 1.0, -1.0], [-2.0, 1.0, 1.0]]) @ normalized_c
            s1 = np.std(s[1, :])
            alpha = (np.std(s[0, :]) / s1) if s1 > 1e-9 else 0.0
            h = s[0, :] + alpha * s[1, :]
            h = h - np.mean(h)
            pulse_accumulator[m:n] = pulse_accumulator[m:n] + h

    bvp = _detrend(pulse_accumulator.reshape(-1, 1), 100.0).flatten()
    nyquist = fs / 2.0
    low_cutoff = max(0.01, 0.75 / nyquist)
    high_cutoff = min(0.99, 8.0 / nyquist)  # Widened to 8.0 Hz to preserve pulse morphology
    b, a = sps.butter(1, [low_cutoff, high_cutoff], btype="bandpass")
    bvp = sps.filtfilt(b, a, bvp.astype(np.double))
    return bvp


def _fft_hr_sqi(bvp: np.ndarray, fs: float, low: float, high: float) -> Tuple[Optional[float], float]:
    """Calculate dominant frequency and spectral SNR (SQI) using Hann window and harmonic weighting."""
    x = bvp.flatten().astype(np.float64)
    n_samples = len(x)
    if n_samples < int(fs * 4.0):
        return None, 0.0

    nfft = _next_power_of_2(n_samples * 2)
    window = sps.windows.hann(n_samples)
    xw = (x - np.mean(x)) * window

    f, pxx = sps.periodogram(xw, fs=fs, nfft=nfft, detrend=False)
    f, pxx = f.flatten(), pxx.flatten()
    band = (f >= low) & (f <= high)
    if not np.any(band):
        return None, 0.0
    total = float(np.sum(pxx[band]))
    if total <= 0:
        return None, 0.0

    band_idx = np.where(band)[0]
    band_f = f[band_idx]
    band_pxx = pxx[band_idx]

    # Candidate peak detection with harmonic scoring:
    # Arterial pulse waves have prominent fundamental (f0) and second harmonic (2*f0).
    # Weighting candidate peaks by their harmonic power rejects spurious low-frequency motion spikes.
    prominence_thresh = max(float(np.max(band_pxx)) * 0.12, 1e-6)
    peaks, _ = sps.find_peaks(band_pxx, prominence=prominence_thresh)

    if len(peaks) > 0:
        best_score = -1.0
        best_f = band_f[peaks[0]]
        for p in peaks:
            f_cand = band_f[p]
            p_fund = band_pxx[p]
            # Second harmonic window around 2 * f_cand
            near_2f = (f >= 2 * f_cand - 0.12) & (f <= 2 * f_cand + 0.12)
            p_harm = float(np.sum(pxx[near_2f])) if np.any(near_2f) else 0.0
            score = p_fund + 0.6 * p_harm
            if score > best_score:
                best_score = score
                best_f = f_cand
        f0 = float(best_f)
    else:
        f0 = float(band_f[int(np.argmax(band_pxx))])

    def near(center: float) -> np.ndarray:
        return (f >= center - 0.1) & (f <= center + 0.1) & band

    peak_power = float(np.sum(pxx[near(f0)]) + np.sum(pxx[near(2 * f0)]))
    sqi = float(np.clip(peak_power / total, 0.0, 1.0))
    return f0, sqi


def resample_uniform(t_ms: np.ndarray, x: np.ndarray, fps: float) -> np.ndarray:
    """Linear interpolate jittered timestamps to uniform fps."""
    t = (t_ms - t_ms[0]) / 1000.0
    dur = t[-1]
    n = max(2, int(round(dur * fps)))
    grid = np.linspace(0.0, dur, n)
    if x.ndim == 1:
        return np.interp(grid, t, x)
    return np.stack([np.interp(grid, t, x[:, c]) for c in range(x.shape[1])], axis=1)


def _resp_rate_sqi(bvp: np.ndarray, fs: float) -> Tuple[Optional[float], float]:
    """Extract respiration from BVP amplitude envelope."""
    env = np.abs(hilbert(bvp))
    env = sp_detrend(env)
    nyquist = fs / 2.0
    low_cutoff = max(0.01, RPPG["RESP_MIN_HZ"] / nyquist)
    high_cutoff = min(0.99, RPPG["RESP_MAX_HZ"] / nyquist)
    b, a = sps.butter(2, [low_cutoff, high_cutoff], btype="bandpass")
    if len(env) <= 3 * max(len(a), len(b)):
        return None, 0.0
    env = sps.filtfilt(b, a, env)
    return _fft_hr_sqi(env, fs, RPPG["RESP_MIN_HZ"], RPPG["RESP_MAX_HZ"])


def analyze_trace(
    t_ms: Sequence[float],
    r: Sequence[float],
    g: Sequence[float],
    b: Sequence[float],
    label: Optional[str] = None,
) -> VitalResult:
    """Analyse one ROI's timestamped RGB trace -> HR + respiration + morphology."""
    t_arr = np.asarray(t_ms, dtype=np.float64)
    rgb = np.stack(
        [
            np.asarray(r, np.float64),
            np.asarray(g, np.float64),
            np.asarray(b, np.float64),
        ],
        axis=1,
    )

    sample_count = len(t_arr)
    dur = (t_arr[-1] - t_arr[0]) / 1000.0 if sample_count >= 2 else 0.0
    fps_eff = (sample_count - 1) / dur if dur > 0 else 0.0

    if sample_count < 16 or dur < RPPG["MIN_DURATION_SEC"]:
        return VitalResult(
            status="too_short",
            hr_bpm=None,
            hr_sqi=0.0,
            resp_bpm=None,
            resp_sqi=0.0,
            duration_sec=float(dur),
            fps_effective=float(fps_eff),
            samples=sample_count,
            bvp=None,
            best_roi=label,
            morphology=None,
        )

    fps = RPPG["FPS_TARGET"]
    rgb_u = resample_uniform(t_arr, rgb, fps)

    bvp = pos_wang(rgb_u, fps)
    hr_hz, hr_sqi = _fft_hr_sqi(bvp, fps, RPPG["HR_MIN_HZ"], RPPG["HR_MAX_HZ"])
    resp_hz, resp_sqi = _resp_rate_sqi(bvp, fps)

    bvp_list = [float(x) for x in bvp]

    if hr_hz is None or hr_sqi < RPPG["SQI_MIN"]:
        return VitalResult(
            status="low_quality",
            hr_bpm=None,
            hr_sqi=float(hr_sqi),
            resp_bpm=None,
            resp_sqi=float(resp_sqi),
            duration_sec=float(dur),
            fps_effective=float(fps_eff),
            samples=sample_count,
            bvp=bvp_list,
            best_roi=label,
            morphology=None,
        )

    hr_bpm = float(hr_hz * 60.0)
    resp_bpm = (
        float(resp_hz * 60.0)
        if (resp_hz is not None and resp_sqi >= RPPG["RESP_SQI_MIN"])
        else None
    )

    # Pulse-Respiration Quotient (PRQ): HR_bpm / Resp_bpm
    prq_val = None
    if hr_bpm is not None and resp_bpm is not None and resp_bpm > 0:
        prq_val = round(float(hr_bpm) / float(resp_bpm), 2)

    morphology_data = None
    sbp_val = None
    dbp_val = None
    bp_cat_val = None
    try:
        morph_res = analyze_waveform(bvp_list, fps)
        if morph_res.get("signal_status") == "ok":
            morphology_data = {
                "systolic_rise_ratio": morph_res.get("systolic_rise_ratio"),
                "diastolic_fall_ratio": morph_res.get("diastolic_fall_ratio"),
                "sw50_sec": morph_res.get("sw50_sec"),
            }
            sbp_val = morph_res.get("systolic_mmhg")
            dbp_val = morph_res.get("diastolic_mmhg")
            bp_cat_val = morph_res.get("bp_category")
    except Exception:
        morphology_data = None

    hrv_data = None
    stress_idx = None
    stress_lvl = None
    stress_lvl_ps = None
    stress_idx_ms = None
    sns_zone_val = None
    pns_zone_val = None
    lf_hf_val = None
    try:
        hrv_res = calculate_hrv_from_bvp(bvp, fps, hr_bpm=hr_bpm)
        if hrv_res.mean_rri_ms is not None:
            # Time-Frequency Reconciliation:
            # When cubic-spline peak detection recovers valid systolic beats,
            # its Mean RRi interval (60000 / Mean RRi) represents the true physical pulse rate.
            # Reconcile if FFT was skewed by low-frequency motion or breathing harmonics.
            if hrv_res.valid_intervals_count >= 5 and hrv_res.mean_rri_ms > 0:
                time_domain_hr = 60000.0 / hrv_res.mean_rri_ms
                if abs(hr_bpm - time_domain_hr) > 4.5:
                    hr_bpm = round(time_domain_hr, 1)
                    if resp_bpm is not None and resp_bpm > 0:
                        prq_val = round(float(hr_bpm) / float(resp_bpm), 2)

            stress_idx = hrv_res.stress_index
            stress_lvl = hrv_res.stress_level
            stress_lvl_ps = hrv_res.stress_level_ps
            stress_idx_ms = hrv_res.stress_index_ms
            sns_zone_val = hrv_res.sns_zone
            pns_zone_val = hrv_res.pns_zone
            lf_hf_val = hrv_res.lf_hf_ratio
            hrv_data = {
                "mean_rri_ms": hrv_res.mean_rri_ms,
                "rmssd_ms": hrv_res.rmssd_ms,
                "sdnn_ms": hrv_res.sdnn_ms,
                "stress_index": hrv_res.stress_index,
                "stress_level": hrv_res.stress_level,
                "stress_level_ps": hrv_res.stress_level_ps,
                "stress_index_ms": hrv_res.stress_index_ms,
                "sns_zone": hrv_res.sns_zone,
                "pns_zone": hrv_res.pns_zone,
                "lf_hf_ratio": hrv_res.lf_hf_ratio,
            }
    except Exception:
        hrv_data = None

    spo2_val = None
    spo2_ratio = None
    try:
        spo2_res = calculate_spo2_from_rgb(
            red_channel=rgb_u[:, 0],
            blue_channel=rgb_u[:, 2],
            fs=fps,
        )
        spo2_val = spo2_res.spo2_percent
        spo2_ratio = spo2_res.ratio_of_ratios
    except Exception:
        spo2_val = None
        spo2_ratio = None

    return VitalResult(
        status="ok",
        hr_bpm=hr_bpm,
        hr_sqi=float(hr_sqi),
        resp_bpm=resp_bpm,
        resp_sqi=float(resp_sqi),
        prq=prq_val,
        stress_index=stress_idx,
        stress_level=stress_lvl,
        stress_level_ps=stress_lvl_ps,
        stress_index_ms=stress_idx_ms,
        sns_zone=sns_zone_val,
        pns_zone=pns_zone_val,
        lf_hf_ratio=lf_hf_val,
        duration_sec=float(dur),
        fps_effective=float(fps_eff),
        samples=sample_count,
        bvp=bvp_list,
        best_roi=label,
        morphology=morphology_data,
        hrv=hrv_data,
        systolic_mmhg=sbp_val,
        diastolic_mmhg=dbp_val,
        bp_category=bp_cat_val,
        spo2_percent=spo2_val,
        spo2_r_ratio=spo2_ratio,
    )


def analyze_rois(rois: List[Dict[str, Any]]) -> VitalResult:
    """Analyse multiple ROIs (forehead + cheeks) and pick the cleanest (highest cardiac SQI)."""
    results: List[VitalResult] = []
    for roi in rois:
        try:
            res = analyze_trace(
                t_ms=roi["t"],
                r=roi["r"],
                g=roi["g"],
                b=roi["b"],
                label=roi.get("label", roi.get("name")),
            )
            results.append(res)
        except Exception:
            continue

    if not results:
        return VitalResult(
            status="no_signal",
            hr_bpm=None,
            hr_sqi=0.0,
            resp_bpm=None,
            resp_sqi=0.0,
            duration_sec=0.0,
            fps_effective=0.0,
            samples=0,
            bvp=None,
            best_roi=None,
            morphology=None,
        )

    ok_results = [x for x in results if x.status == "ok"]
    if ok_results:
        return max(ok_results, key=lambda x: x.hr_sqi)
    return max(results, key=lambda x: x.hr_sqi)

