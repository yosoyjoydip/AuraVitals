import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.blood_pressure import analyze_waveform

client = TestClient(app)


def make_pulse_waveform(
    sampling_rate_hz: int = 30, duration_sec: int = 20
) -> list[float]:
    time = np.arange(sampling_rate_hz * duration_sec) / sampling_rate_hz
    phase = (time * 1.2) % 1
    return np.where(phase < 0.3, phase / 0.3, (1 - phase) / 0.7).tolist()


def test_extracts_morphology_and_computes_regression_blood_pressure() -> None:
    result = analyze_waveform(make_pulse_waveform(), 30)

    assert result["signal_status"] == "ok"
    assert abs(result["heart_rate_bpm"] - 72) < 3
    assert result["systolic_rise_ratio"] is not None
    assert result["diastolic_fall_ratio"] is not None
    assert result["sw50_sec"] is not None
    assert result["systolic_mmhg"] is not None
    assert 90.0 <= result["systolic_mmhg"] <= 145.0
    assert result["diastolic_mmhg"] is not None
    assert 60.0 <= result["diastolic_mmhg"] <= 95.0
    assert result["systolic_mmhg"] > result["diastolic_mmhg"]
    assert result["calibration_status"] == "morphology_calibrated"
    assert result["bp_category"] in ("Normal", "Elevated", "Hypertension Stage 1", "Hypertension Stage 2")


def test_analysis_endpoint_returns_signal_features() -> None:
    response = client.post(
        "/api/v1/blood-pressure/analyze",
        json={"waveform": make_pulse_waveform(), "sampling_rate_hz": 30},
    )

    assert response.status_code == 200
    assert response.json()["signal_status"] == "ok"
    assert response.json()["systolic_mmhg"] is not None
    assert response.json()["diastolic_mmhg"] is not None
    assert response.json()["calibration_status"] == "morphology_calibrated"


def test_analysis_endpoint_rejects_short_waveform() -> None:
    response = client.post(
        "/api/v1/blood-pressure/analyze",
        json={"waveform": [0.0] * 100, "sampling_rate_hz": 30},
    )

    assert response.status_code == 422
