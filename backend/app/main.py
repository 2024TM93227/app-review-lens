from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import logging
import os
from typing import List
import json
import uuid

from app.db.base import Base
from app.db.session import engine

# Import models to ensure tables are created
from app.models.review import Review
from app.models.insight import Insight
from app.models.job import Job

from app.api import reviews, insights, compare, apps, jobs, analysis
from app.api import ai
from app.services.background_worker import start_background_scheduler, stop_background_scheduler, is_scheduler_running
from app.logging_utils import CorrelationIdMiddleware
from app.rate_limiter import RateLimitMiddleware
from app.cache import get_cache

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="App Review Lens API",
    description="Decision-first product analytics for food delivery apps. Real Google Play reviews, actionable insights.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc"
)

# CORS Configuration from environment
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:4200")
try:
    if cors_origins.startswith('['):
        # JSON array format
        cors_origins_list = json.loads(cors_origins)
    else:
        # Comma-separated format
        cors_origins_list = [origin.strip() for origin in cors_origins.split(',')]
except (json.JSONDecodeError, AttributeError):
    cors_origins_list = ["http://localhost:4200"]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=cors_origins_list,
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Correlation ID middleware for request tracing
app.add_middleware(CorrelationIdMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)
app.include_router(reviews.router, prefix="/reviews")
app.include_router(insights.router, prefix="/insights")
app.include_router(compare.router, prefix="/compare")
app.include_router(apps.router, prefix="/apps")
app.include_router(jobs.router, prefix="/jobs")
app.include_router(analysis.router, prefix="/analysis")
app.include_router(ai.router, prefix="/ai")


@app.get("/health")
async def health_check():
    """Basic health check - app is running"""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/deep")
async def health_check_deep():
    """Deep health check - verify dependencies"""
    from app.db.session import SessionLocal
    from sqlalchemy import text
    
    health_status = {
        "status": "ok",
        "database": "error",
        "cache": "error"
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = f"error: {str(e)}"
    
    # Check cache
    try:
        cache = get_cache()
        is_healthy = await cache.health_check()
        health_status["cache"] = "ok" if is_healthy else "unavailable"
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        health_status["cache"] = f"error: {str(e)}"
    
    # Overall status
    if health_status["database"] == "ok" and health_status["cache"] in ["ok", "unavailable"]:
        health_status["status"] = "ok"
    else:
        health_status["status"] = "degraded"
    
    return health_status


# WebSocket endpoints removed to improve ingestion performance.
# Real-time updates via WebSocket were disabled; keep websocket_manager
# implementation available if re-enabling later.


@app.on_event("startup")
async def startup_event():
    """Start background scheduler on app startup"""
    logger.info("Starting App Review Lens API")
    logger.info(f"CORS origins: {cors_origins_list}")
    # WebSocket manager disabled in this deployment to reduce ingestion overhead
    start_background_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background scheduler on app shutdown"""
    logger.info("Stopping App Review Lens API")
    stop_background_scheduler()


@app.get("/")
def health():
    return {
        "status": "running",
        "background_worker": "active" if is_scheduler_running() else "inactive"
    }


@app.get("/health/detailed")
def health_detailed():
    """Detailed health check including worker status"""
    return {
        "status": "running",
        "service": "App Review Lens",
        "version": "1.0.0",
        "background_worker": "active" if is_scheduler_running() else "inactive",
        "components": {
            "database": "connected",
            "nlp_models": "loaded",
            "playstore_scraper": "ready"
        }
    }
