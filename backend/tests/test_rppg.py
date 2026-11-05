import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.rppg import analyze_rois, analyze_trace, pos_wang, resample_uniform

client = TestClient(app)


def make_synthetic_roi(
    duration_sec: float = 15.0,
    hr_bpm: float = 72.0,
    resp_bpm: float = 15.0,
    fps: float = 30.0,
    noise_level: float = 0.01,
    label: str = "forehead",
) -> dict[str, list[float] | str]:
    num_samples = int(duration_sec * fps)
    time_sec = np.linspace(0.0, duration_sec, num_samples)
    t_ms = (time_sec * 1000.0).tolist()

    hr_hz = hr_bpm / 60.0
    resp_hz = resp_bpm / 60.0

    cardiac_signal = np.sin(2 * np.pi * hr_hz * time_sec)
    resp_mod = 1.0 + 0.3 * np.sin(2 * np.pi * resp_hz * time_sec)
    pulse = cardiac_signal * resp_mod

    # Facial skin baseline color ~ (R=180, G=130, B=110)
    # Green channel has strongest hemoglobin absorption oscillation
    r = (180.0 + 0.5 * pulse + np.random.normal(0, noise_level, num_samples)).tolist()
    g = (130.0 + 2.0 * pulse + np.random.normal(0, noise_level, num_samples)).tolist()
    b = (110.0 + 0.3 * pulse + np.random.normal(0, noise_level, num_samples)).tolist()

    return {
        "label": label,
        "t": t_ms,
        "r": r,
        "g": g,
        "b": b,
    }


def test_resample_uniform() -> None:
    t_ms = np.array([0, 35, 68, 102, 134, 167], dtype=np.float64)
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float64)
    uniform_x = resample_uniform(t_ms, x, fps=30.0)
    assert len(uniform_x) >= 2
    assert not np.isnan(uniform_x).any()


def test_pos_wang_extracts_bvp() -> None:
    roi = make_synthetic_roi(duration_sec=15.0, hr_bpm=72.0, noise_level=0.001)
    rgb = np.stack([roi["r"], roi["g"], roi["b"]], axis=1)
    bvp = pos_wang(rgb, fs=30.0)
    assert len(bvp) == len(roi["t"])
    assert not np.isnan(bvp).any()


def test_analyze_trace_recovers_hr_and_respiration() -> None:
    roi = make_synthetic_roi(duration_sec=16.0, hr_bpm=72.0, resp_bpm=14.0, noise_level=0.005)
    result = analyze_trace(roi["t"], roi["r"], roi["g"], roi["b"], label="forehead")

    assert result.status == "ok"
    assert result.hr_bpm is not None
    assert abs(result.hr_bpm - 72.0) < 5.0
    assert result.hr_sqi >= 0.25
    assert result.bvp is not None
    assert len(result.bvp) > 0


def test_analyze_trace_refuses_short_trace() -> None:
    roi = make_synthetic_roi(duration_sec=5.0)
    result = analyze_trace(roi["t"], roi["r"], roi["g"], roi["b"])
    assert result.status == "too_short"
    assert result.hr_bpm is None


def test_analyze_rois_picks_cleanest_roi() -> None:
    clean_roi = make_synthetic_roi(duration_sec=15.0, hr_bpm=72.0, noise_level=0.001, label="forehead")
    noisy_roi = make_synthetic_roi(duration_sec=15.0, hr_bpm=72.0, noise_level=5.0, label="cheek_shadowed")

    result = analyze_rois([clean_roi, noisy_roi])
    assert result.status == "ok"
    assert result.best_roi == "forehead"


def test_rppg_endpoint_success() -> None:
    roi = make_synthetic_roi(duration_sec=15.0, hr_bpm=75.0, resp_bpm=15.0, noise_level=0.005)
    response = client.post(
        "/api/v1/rppg/analyze",
        json={"rois": [roi]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["heart_rate_bpm"] is not None
    assert abs(data["heart_rate_bpm"] - 75.0) < 5.0
    assert data["hr_sqi"] >= 0.25
    assert data["bvp"] is not None
    assert data["calibration_status"] in ("morphology_calibrated", "uncalibrated")
    if data["blood_pressure"] is not None:
        assert data["blood_pressure"]["systolic_mmhg"] is not None
        assert data["blood_pressure"]["diastolic_mmhg"] is not None
    # Verify PRQ and Stress metrics
    assert "prq" in data
    assert "stress_index" in data
    assert "stress_level" in data
    if data["heart_rate_bpm"] and data["resp_bpm"] and data["resp_bpm"] > 0:
        expected_prq = round(data["heart_rate_bpm"] / data["resp_bpm"], 2)
        assert data["prq"] == expected_prq

