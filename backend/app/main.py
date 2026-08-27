import logging
import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.api import api_router
from app.ml.recovery_probability_model import RecoveryProbabilityModelService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RevenueShield Recovery AI Platform",
    description="Enterprise Autonomous Revenue Recovery, Voice AI, and Decision Engine",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Parse explicit allowed origins from environment configuration
raw_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if not raw_origins or "*" in raw_origins:
    allowed_origins = ["*"]
    allow_credentials = False
else:
    allowed_origins = raw_origins
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global safe error handler in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[GLOBAL_EXCEPTION] Unhandled error at {request.method} {request.url.path}: {exc}", exc_info=True)
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error occurred. Operational reference logged."},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )

app.include_router(api_router)

# Mount Frontend Static Assets & Application
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")

    @app.get("/portal", tags=["Frontend Portal"], include_in_schema=False)
    @app.get("/portal/{case_id}", tags=["Frontend Portal"], include_in_schema=False)
    def serve_frontend_portal(case_id: str = None) -> FileResponse:
        """Serve the Customer AI Voice Recovery Portal HTML."""
        index_file = FRONTEND_DIR / "index.html"
        return FileResponse(str(index_file))


@app.get("/", tags=["Root"])
def root_endpoint() -> Dict[str, str]:
    """Root endpoint welcoming requests and pointing to documentation."""
    return {
        "service": "RevenueShield Recovery AI Platform",
        "status": "online",
        "health_url": "/health",
        "ready_url": "/health/ready",
        "portal_url": "/portal",
        "webhook_url": "/webhooks/razorpay",
    }


@app.get("/health", response_model=Dict[str, str], tags=["Health"])
def health_check() -> Dict[str, str]:
    """Liveness health check endpoint to verify backend service availability."""
    return {"status": "ok"}


@app.get("/health/db", response_model=Dict[str, str], tags=["Health"])
def database_health_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """Database connectivity health check without exposing credentials or internal topology."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "disconnected"},
        )


@app.get("/health/ready", response_model=Dict[str, Any], tags=["Health"])
def readiness_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Readiness probe checking database and ML model readiness without leaking internal secrets."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.warning(f"[HEALTH_READY_DB_ERROR] Database ping failed: {e}")

    model_loaded = RecoveryProbabilityModelService.load_model() is not None

    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "disconnected",
                "model_status": "active" if model_loaded else "cold_start",
            },
        )

    return {
        "status": "ready",
        "database": "connected",
        "model_status": "active" if model_loaded else "cold_start",
    }
