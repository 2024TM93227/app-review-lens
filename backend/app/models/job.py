from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, JSON, Enum as SQLEnum, Index
from datetime import datetime
from app.db.base import Base
import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # UUID job ID
    
    # Job metadata
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, index=True)
    job_type = Column(String)  # "ingest_reviews", "generate_insights", "compare"
    
    # Input parameters
    app_ids = Column(JSON)  # List of app IDs
    countries = Column(JSON, default=["IN"])
    languages = Column(JSON, default=["en"])
    since_date = Column(String, nullable=True)
    until_date = Column(String, nullable=True)
    max_reviews = Column(Integer, default=1000)
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    total_reviews_to_ingest = Column(Integer, default=0)
    reviews_ingested = Column(Integer, default=0)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_retry_at = Column(DateTime, nullable=True)
    
    # Priority and cancellation
    priority = Column(Integer, default=5, index=True)  # 1-10, higher = more urgent
    cancelled_at = Column(DateTime, nullable=True)
    
    # Incremental ingestion
    last_ingested_timestamp = Column(DateTime, nullable=True)  # For incremental fetching
    
    # Messages
    message = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results storage
    result_data = Column(JSON, nullable=True)  # Contains final analysis data
    
    # Audit
    created_by = Column(String, nullable=True)

    # Table-level constraints and indices
    __table_args__ = (
        Index('ix_job_status_created', 'status', 'created_at'),  # For polling active jobs
        Index('ix_job_status_priority', 'status', 'priority'),  # For query by status, order by priority
        Index('ix_job_created_at', 'created_at'),  # For time-based queries
        Index('ix_job_cancelled', 'cancelled_at'),  # For finding cancelled jobs
    )
