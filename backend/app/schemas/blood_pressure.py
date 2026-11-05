from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BloodPressureAnalysisRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    waveform: list[float] = Field(min_length=205, max_length=14_401)
    sampling_rate_hz: float = Field(ge=17, le=120)

    @model_validator(mode="after")
    def validate_duration(self) -> "BloodPressureAnalysisRequest":
        duration_sec = (len(self.waveform) - 1) / self.sampling_rate_hz
        if not 12 <= duration_sec <= 120:
            raise ValueError("waveform duration must be between 12 and 120 seconds")
        return self


class BloodPressureAnalysisResponse(BaseModel):
    signal_status: Literal["ok", "low_quality"]
    heart_rate_bpm: float | None
    systolic_rise_ratio: float | None
    diastolic_fall_ratio: float | None
    sw50_sec: float | None
    mean_rri_ms: float | None = None
    rmssd_ms: float | None = None
    sdnn_ms: float | None = None
    stress_index: float | None = None
    stress_level: str | None = None
    systolic_mmhg: float | None = None
    diastolic_mmhg: float | None = None
    bp_category: str | None = None
    calibration_status: Literal["uncalibrated", "morphology_calibrated"] = "morphology_calibrated"
    disclaimer: str = (
        "Pulse morphology linear regression estimate; anchored to healthy adult baselines. "
        "Not a diagnostic replacement for clinical cuff measurements."
    )
