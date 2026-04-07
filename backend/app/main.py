from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.db.base import Base
from app.db.session import engine
from app.api import reviews, insights, compare
from app.api import ai
from app.services.background_worker import start_background_scheduler, stop_background_scheduler, is_scheduler_running

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="App Review Lens")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:4201", "http://localhost:3000"],  # use ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(reviews.router, prefix="/reviews")
app.include_router(insights.router, prefix="/insights")
app.include_router(compare.router, prefix="/compare")
app.include_router(ai.router, prefix="/ai")


@app.on_event("startup")
async def startup_event():
    """Start background scheduler on app startup"""
    logger.info("Starting App Review Lens API")
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
