import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.spo2 import calculate_spo2_from_rgb
from tests.test_rppg import make_synthetic_roi

client = TestClient(app)


def test_spo2_normal_oxygenation() -> None:
    fs = 30.0
    duration_sec = 15.0
    t = np.arange(int(duration_sec * fs)) / fs
    pulse = np.sin(2 * np.pi * 1.2 * t)  # 72 bpm cardiac oscillation

    # Normal healthy oxygenation: R ~ 0.36 -> SpO2 ~ 97-98%
    # DC_Red = 180.0, AC_Red ~ 0.60
    # DC_Blue = 110.0, AC_Blue ~ 1.00
    red = 180.0 + 0.60 * pulse
    blue = 110.0 + 1.00 * pulse

    res = calculate_spo2_from_rgb(red.tolist(), blue.tolist(), fs=fs)

    assert res.spo2_percent is not None
    assert 96.0 <= res.spo2_percent <= 100.0
    assert res.ratio_of_ratios is not None
    assert 0.25 <= res.ratio_of_ratios <= 0.45


def test_spo2_hypoxic_condition() -> None:
    fs = 30.0
    duration_sec = 15.0
    t = np.arange(int(duration_sec * fs)) / fs
    pulse = np.sin(2 * np.pi * 1.2 * t)

    # Hypoxic condition: higher R ~ 1.0 -> SpO2 ~ 91.4%
    # DC_Red = 180.0, AC_Red ~ 1.65
    # DC_Blue = 110.0, AC_Blue ~ 1.00
    red = 180.0 + 1.65 * pulse
    blue = 110.0 + 1.00 * pulse

    res = calculate_spo2_from_rgb(red.tolist(), blue.tolist(), fs=fs)

    assert res.spo2_percent is not None
    assert 90.0 <= res.spo2_percent <= 94.0
    assert res.ratio_of_ratios is not None
    assert res.ratio_of_ratios > 0.60


def test_spo2_clamping_bounds() -> None:
    fs = 30.0
    t = np.arange(int(15.0 * fs)) / fs
    pulse = np.sin(2 * np.pi * 1.2 * t)

    # Extreme high R -> raw SpO2 < 90 -> clamped to 90.0%
    red_low_o2 = 180.0 + 3.0 * pulse
    blue_low_o2 = 110.0 + 0.8 * pulse
    res_low = calculate_spo2_from_rgb(red_low_o2.tolist(), blue_low_o2.tolist(), fs=fs)
    assert res_low.spo2_percent == 90.0

    # Extreme low R -> raw SpO2 > 100 -> clamped to 100.0%
    red_high_o2 = 180.0 + 0.1 * pulse
    blue_high_o2 = 110.0 + 2.0 * pulse
    res_high = calculate_spo2_from_rgb(red_high_o2.tolist(), blue_high_o2.tolist(), fs=fs)
    assert res_high.spo2_percent == 100.0


def test_rppg_endpoint_returns_spo2() -> None:
    roi = make_synthetic_roi(duration_sec=15.0, hr_bpm=75.0, noise_level=0.002)
    response = client.post(
        "/api/v1/rppg/analyze",
        json={"rois": [roi]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "spo2_percent" in data
    assert data["spo2_percent"] is not None
    assert 90.0 <= data["spo2_percent"] <= 100.0

