import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.hrv import calculate_hrv_from_bvp, calculate_stress_index
from tests.test_blood_pressure import make_pulse_waveform
from tests.test_rppg import make_synthetic_roi

client = TestClient(app)


def test_hrv_mean_rri_accuracy() -> None:
    # 75 bpm => 1.25 Hz => period = 0.800 s = 800.0 ms
    fs = 30.0
    duration_sec = 20.0
    t = np.arange(int(duration_sec * fs)) / fs
    # BVP pulse wave with peaks at 1.25 Hz
    bvp = np.sin(2 * np.pi * 1.25 * t)

    res = calculate_hrv_from_bvp(bvp.tolist(), fs=fs)

    assert res.mean_rri_ms is not None
    # Within 4 ms resolution (250 Hz target grid)
    assert abs(res.mean_rri_ms - 800.0) <= 6.0
    assert res.peak_count >= 20
    assert res.valid_intervals_count >= 19


def test_hrv_outlier_filtering() -> None:
    fs = 30.0
    duration_sec = 25.0
    t = np.arange(int(duration_sec * fs)) / fs
    # Regular 72 bpm => 1.2 Hz => 833.3 ms
    bvp = np.sin(2 * np.pi * 1.2 * t)

    # Corrupt one region by zeroing/flattening to create an abnormally long interval (> 30% jump)
    corrupted_bvp = bvp.copy()
    corrupted_bvp[int(10 * fs) : int(12 * fs)] = 0.0

    res = calculate_hrv_from_bvp(corrupted_bvp.tolist(), fs=fs)
    assert res.mean_rri_ms is not None
    # Outlier (>30% jump) should be filtered out, preserving accurate mean RRi ~ 833 ms
    assert abs(res.mean_rri_ms - 833.3) < 15.0


def test_calculate_stress_index_scales() -> None:
    # High vagal tone / high RMSSD (80 ms) -> Relaxed (low stress score ~ 5)
    stress_idx_low, level_low = calculate_stress_index(80.0)
    assert stress_idx_low is not None
    assert stress_idx_low <= 30.0
    assert level_low == "Relaxed"

    # Moderate RMSSD (45 ms) -> Normal
    stress_idx_mid, level_mid = calculate_stress_index(45.0)
    assert stress_idx_mid is not None
    assert 30.0 < stress_idx_mid <= 55.0
    assert level_mid == "Normal"

    # Low RMSSD (12 ms) -> High Stress
    stress_idx_high, level_high = calculate_stress_index(12.0)
    assert stress_idx_high is not None
    assert stress_idx_high >= 75.0
    assert level_high == "High Stress"

    # None or zero check
    assert calculate_stress_index(None) == (None, None)
    assert calculate_stress_index(0.0) == (None, None)


def test_hrv_rmssd_and_sdnn_computed() -> None:
    # 20s pulse waveform from test_blood_pressure
    waveform = make_pulse_waveform(sampling_rate_hz=30, duration_sec=20)
    res = calculate_hrv_from_bvp(waveform, fs=30.0)

    assert res.mean_rri_ms is not None
    assert res.rmssd_ms is not None
    assert res.sdnn_ms is not None
    assert res.rmssd_ms >= 0.0
    assert res.sdnn_ms >= 0.0
    assert res.stress_index is not None
    assert res.stress_level in ("Relaxed", "Normal", "Elevated", "High Stress")


def test_blood_pressure_endpoint_returns_hrv() -> None:
    response = client.post(
        "/api/v1/blood-pressure/analyze",
        json={"waveform": make_pulse_waveform(), "sampling_rate_hz": 30},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["signal_status"] == "ok"
    assert "mean_rri_ms" in data
    assert data["mean_rri_ms"] is not None
    assert "rmssd_ms" in data
    assert "sdnn_ms" in data
    assert "stress_index" in data
    assert "stress_level" in data


def test_rppg_endpoint_returns_hrv() -> None:
    roi = make_synthetic_roi(duration_sec=16.0, hr_bpm=75.0, noise_level=0.002)
    response = client.post(
        "/api/v1/rppg/analyze",
        json={"rois": [roi]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["hrv"] is not None
    assert data["hrv"]["mean_rri_ms"] is not None
    assert abs(data["hrv"]["mean_rri_ms"] - 800.0) < 25.0
    assert data["hrv"]["rmssd_ms"] is not None
    assert data["hrv"]["sdnn_ms"] is not None
    assert data["hrv"]["stress_index"] is not None
    assert data["hrv"]["stress_level"] in ("Relaxed", "Normal", "Elevated", "High Stress")

