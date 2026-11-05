import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_root = str(Path(__file__).resolve().parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.blood_pressure import router as blood_pressure_router
from app.api.routes.rppg import router as rppg_router

app = FastAPI(
    title="AuraVitals API",
    version="0.1.0",
    description="Pulse morphology research API; not a diagnostic medical device.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(blood_pressure_router)
app.include_router(rppg_router)
