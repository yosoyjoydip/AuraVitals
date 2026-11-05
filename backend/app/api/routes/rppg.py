from fastapi import APIRouter

from app.schemas.rppg import RppgAnalysisRequest, RppgAnalysisResponse
from app.services.rppg import analyze_rois

router = APIRouter(prefix="/api/v1/rppg", tags=["rppg"])


@router.post("/analyze", response_model=RppgAnalysisResponse)
def analyze_rppg_signals(request: RppgAnalysisRequest) -> RppgAnalysisResponse:
    roi_dicts = [
        {
            "label": roi.label,
            "t": roi.t,
            "r": roi.r,
            "g": roi.g,
            "b": roi.b,
        }
        for roi in request.rois
    ]
    result = analyze_rois(roi_dicts)
    return RppgAnalysisResponse(
        status=result.status,
        heart_rate_bpm=result.hr_bpm,
        hr_sqi=result.hr_sqi,
        resp_bpm=result.resp_bpm,
        resp_sqi=result.resp_sqi,
        prq=result.prq,
        stress_index=result.stress_index,
        stress_level=result.stress_level,
        stress_level_ps=result.stress_level_ps,
        stress_index_ms=result.stress_index_ms,
        sns_zone=result.sns_zone,
        pns_zone=result.pns_zone,
        lf_hf_ratio=result.lf_hf_ratio,
        duration_sec=result.duration_sec,
        fps_effective=result.fps_effective,
        samples=result.samples,
        best_roi=result.best_roi,
        bvp=result.bvp,
        morphology=(
            result.morphology
            if result.morphology is not None
            else None
        ),
        hrv=(
            result.hrv
            if result.hrv is not None
            else None
        ),
        blood_pressure=(
            {
                "systolic_mmhg": result.systolic_mmhg,
                "diastolic_mmhg": result.diastolic_mmhg,
                "category": result.bp_category,
                "calibration_status": "morphology_calibrated",
            }
            if result.systolic_mmhg is not None
            else None
        ),
        spo2_percent=result.spo2_percent,
        spo2_r_ratio=result.spo2_r_ratio,
        calibration_status=(
            "morphology_calibrated"
            if result.systolic_mmhg is not None
            else "uncalibrated"
        ),
    )

