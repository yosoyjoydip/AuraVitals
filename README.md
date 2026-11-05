# AuraVitals

AuraVitals is a contactless physiological sensing and pulse morphology research platform.
It combines a camera-based remote photoplethysmography (rPPG) engine (POS Wang et al. 2017)
with cardiac cycle morphology analysis (systolic rise, diastolic fall, and SW50 width).

> **Not for diagnosis or treatment.** This version reports rPPG vitals (heart rate, respiration,
> and pulse morphology) only. It deliberately does not estimate systolic or diastolic
> blood pressure: those values require regression calibrated and validated against
> paired clinical cuff measurements.

## Project layout

```text
AuraVitals/
+-- rppg.py                   # Standalone POS rPPG engine
+-- backend/
|   +-- app/
|   |   +-- api/routes/       # Versioned HTTP endpoints (rppg, blood_pressure)
|   |   +-- schemas/          # Pydantic request and response validation
|   |   +-- services/         # Signal processing (POS, detrending, morphology)
|   |   +-- main.py           # FastAPI application
|   +-- tests/                # Pytest suites
|   +-- requirements.txt
+-- frontend/
    +-- src/
    |   +-- components/       # CameraCapture (ROI extraction) & WaveformChart
    |   +-- api/              # API clients for rPPG & Blood Pressure
    |   +-- App.tsx           # Dashboard UI
    +-- package.json
    +-- vite.config.ts
```

## Run the backend

From the repository root, create and activate a virtual environment, then run:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The API is available at `http://localhost:8000`; interactive OpenAPI documentation
is at `http://localhost:8000/docs`.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to the local FastAPI server.

## API Endpoints

### 1. rPPG Multi-ROI Analysis
`POST /api/v1/rppg/analyze`

Send timestamped RGB traces from facial regions (forehead, left cheek, right cheek):

```json
{
  "rois": [
    {
      "label": "forehead",
      "t": [0, 33.3, 66.7, ...],
      "r": [178.2, 178.5, ...],
      "g": [128.4, 129.1, ...],
      "b": [108.9, 109.2, ...]
    }
  ]
}
```

Returns heart rate (bpm), cardiac SQI, respiration (breaths/min), respiration SQI,
recovered Blood-Volume Pulse (BVP) waveform, and pulse morphology.

### 2. Blood Pressure / Pulse Morphology Request
`POST /api/v1/blood-pressure/analyze`

Send a finite numeric `waveform` array and `sampling_rate_hz` (12 to 120 seconds at 17 to 120 Hz).
Responses include heart rate, systolic-rise ratio, diastolic-fall ratio, and
SW50 in seconds. BP values stay `null` and `calibration_status` stays `uncalibrated`.

## Run tests

```powershell
python -m pytest backend\tests
```
