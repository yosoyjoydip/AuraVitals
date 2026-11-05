from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RoiTrace(BaseModel):
    label: str = Field(default="roi", description="e.g. forehead, left_cheek, right_cheek")
    t: list[float] = Field(min_length=16, description="Timestamps in milliseconds")
    r: list[float] = Field(min_length=16, description="Mean Red channel values")
    g: list[float] = Field(min_length=16, description="Mean Green channel values")
    b: list[float] = Field(min_length=16, description="Mean Blue channel values")

    @model_validator(mode="after")
    def validate_lengths(self) -> "RoiTrace":
        length = len(self.t)
        if not (len(self.r) == length and len(self.g) == length and len(self.b) == length):
            raise ValueError("t, r, g, and b arrays must have identical lengths")
        return self


class RppgAnalysisRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    rois: list[RoiTrace] = Field(min_length=1, max_length=10)


class PulseMorphology(BaseModel):
    systolic_rise_ratio: float | None = None
    diastolic_fall_ratio: float | None = None
    sw50_sec: float | None = None


class HrvMetrics(BaseModel):
    mean_rri_ms: float | None = None
    rmssd_ms: float | None = None
    sdnn_ms: float | None = None
    stress_index: float | None = None
    stress_level: str | None = None


class BloodPressureEstimate(BaseModel):
    systolic_mmhg: float | None = None
    diastolic_mmhg: float | None = None
    category: str | None = None
    calibration_status: Literal["uncalibrated", "morphology_calibrated"] = "morphology_calibrated"


class RppgAnalysisResponse(BaseModel):
    status: Literal["ok", "low_quality", "too_short", "no_signal"]
    heart_rate_bpm: float | None = None
    hr_sqi: float = 0.0
    resp_bpm: float | None = None
    resp_sqi: float = 0.0
    prq: float | None = None
    stress_index: float | None = None
    stress_level: str | None = None
    duration_sec: float = 0.0
    fps_effective: float = 0.0
    samples: int = 0
    best_roi: str | None = None
    bvp: list[float] | None = None
    morphology: PulseMorphology | None = None
    hrv: HrvMetrics | None = None
    blood_pressure: BloodPressureEstimate | None = None
    spo2_percent: float | None = None
    spo2_r_ratio: float | None = None
    calibration_status: Literal["uncalibrated", "morphology_calibrated"] = "morphology_calibrated"
    disclaimer: str = (
        "AuraVitals rPPG is an experimental vital-signs research tool. "
        "Not intended for medical diagnosis, treatment, or clinical decisions."
    )

