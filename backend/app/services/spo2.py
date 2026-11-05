"""
Blood Oxygen Saturation (SpO2) processing engine.

Core Principle:
Visible-light rPPG pulse oximetry uses the differential absorption of
oxygenated (HbO2) and deoxygenated (Hb) hemoglobin across Red and Blue channels:

1. AC/DC Decomposition:
   - DC (Baseline): Steady average brightness of skin tissue and ambient light:
     DC = np.mean(channel)
   - AC (Pulsatile Wave): Heartbeat-induced ripple:
     AC = np.std(bandpass_filtered(channel))

2. Ratio-of-Ratios (R):
   R = (AC_Red / DC_Red) / (AC_Blue / DC_Blue)

3. Linear Mapping & Clamping:
   SpO2 = 108.0 - 16.5 * R (calibrated for ambient visible-light mobile cameras)
   Clamped between 90.0% and 100.0%.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence

import numpy as np
from scipy import signal as sps


@dataclass
class Spo2Result:
    spo2_percent: Optional[float] = None
    ratio_of_ratios: Optional[float] = None
    ac_red: Optional[float] = None
    dc_red: Optional[float] = None
    ac_blue: Optional[float] = None
    dc_blue: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_spo2_from_rgb(
    red_channel: Sequence[float],
    blue_channel: Sequence[float],
    fs: float = 30.0,
    low_hz: float = 0.75,
    high_hz: float = 3.0,
) -> Spo2Result:
    """Calculate SpO2 percentage using AC/DC decomposition and the Ratio-of-Ratios.

    Parameters:
    -----------
    red_channel:
        1D array of mean Red channel intensity values.
    blue_channel:
        1D array of mean Blue channel intensity values.
    fs:
        Sampling frequency in Hz (default 30.0 Hz).
    low_hz:
        Lower cutoff for cardiac bandpass (default 0.75 Hz = 45 bpm).
    high_hz:
        Upper cutoff for cardiac bandpass (default 3.0 Hz = 180 bpm).
    """
    r_arr = np.asarray(red_channel, dtype=np.float64)
    b_arr = np.asarray(blue_channel, dtype=np.float64)

    if len(r_arr) < int(fs * 4.0) or len(b_arr) < int(fs * 4.0):
        return Spo2Result()

    # 1. DC Component (Baseline steady brightness)
    dc_red = float(np.mean(r_arr))
    dc_blue = float(np.mean(b_arr))

    if dc_red <= 1e-6 or dc_blue <= 1e-6:
        return Spo2Result(dc_red=dc_red, dc_blue=dc_blue)

    # 2. AC Component (Cardiac pulsatile wave)
    nyquist = fs / 2.0
    low_cutoff = max(0.01, low_hz / nyquist)
    high_cutoff = min(0.99, high_hz / nyquist)
    b, a = sps.butter(2, [low_cutoff, high_cutoff], btype="bandpass")

    ac_red_wave = sps.filtfilt(b, a, r_arr)
    ac_blue_wave = sps.filtfilt(b, a, b_arr)

    ac_red = float(np.std(ac_red_wave))
    ac_blue = float(np.std(ac_blue_wave))

    if ac_blue <= 1e-8:
        return Spo2Result(
            ac_red=ac_red,
            dc_red=dc_red,
            ac_blue=ac_blue,
            dc_blue=dc_blue,
        )

    # 3. Ratio-of-Ratios (R)
    normalized_red = ac_red / dc_red
    normalized_blue = ac_blue / dc_blue

    if normalized_blue <= 1e-8:
        return Spo2Result(
            ac_red=ac_red,
            dc_red=dc_red,
            ac_blue=ac_blue,
            dc_blue=dc_blue,
        )

    r_ratio = float(normalized_red / normalized_blue)

    # 4. Calibrated Linear Mapping & Physiological Clamping
    # SpO2 = 108.0 - 16.5 * R (calibrated for ambient mobile camera RGB sensors)
    raw_spo2 = 108.0 - 16.5 * r_ratio
    clamped_spo2 = float(np.clip(raw_spo2, 90.0, 100.0))

    return Spo2Result(
        spo2_percent=round(clamped_spo2, 1),
        ratio_of_ratios=round(r_ratio, 4),
        ac_red=round(ac_red, 4),
        dc_red=round(dc_red, 4),
        ac_blue=round(ac_blue, 4),
        dc_blue=round(dc_blue, 4),
    )

