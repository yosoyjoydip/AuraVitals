from fastapi import APIRouter

from app.schemas.blood_pressure import (
    BloodPressureAnalysisRequest,
    BloodPressureAnalysisResponse,
)
from app.services.blood_pressure import analyze_waveform

router = APIRouter(prefix="/api/v1/blood-pressure", tags=["blood pressure"])


@router.post("/analyze", response_model=BloodPressureAnalysisResponse)
def analyze_blood_pressure(
    request: BloodPressureAnalysisRequest,
) -> BloodPressureAnalysisResponse:
    return analyze_waveform(request.waveform, request.sampling_rate_hz)
