"""
Unit tests for app/models/job.py and app/api/jobs.py
Tests job creation, status tracking, and retry logic
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.db.base import Base
from app.models.job import Job, JobStatus
from app.api.schemas import IngestReviewsRequest, IngestReviewsResponse


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    engine.dispose()


class TestJobModel:
    """Tests for Job model"""
    
    def test_job_creation(self, test_db):
        """Test creating a new job"""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            job_type='ingest_reviews',
            status=JobStatus.QUEUED,
            app_ids=['in.swiggy.android'],
            countries=['IN'],
            languages=['en'],
            max_reviews=1000
        )
        
        assert job.id == job_id
        assert job.status == JobStatus.QUEUED
        assert job.app_ids == ['in.swiggy.android']
        assert job.progress == 0.0
        assert job.retry_count == 0
        assert job.max_retries == 3

    def test_job_status_enum(self):
        """Test JobStatus enum values"""
        assert JobStatus.QUEUED.value == 'queued'
        assert JobStatus.PROCESSING.value == 'processing'
        assert JobStatus.RETRYING.value == 'retrying'
        assert JobStatus.COMPLETED.value == 'completed'
        assert JobStatus.FAILED.value == 'failed'

    def test_job_persistence(self, test_db):
        """Test saving and retrieving job from database"""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            job_type='ingest_reviews',
            status=JobStatus.QUEUED,
            app_ids=['com.application.zomato'],
            progress=25.5,
            message='First 250 reviews ingested'
        )
        
        test_db.add(job)
        test_db.commit()
        
        # Retrieve
        retrieved = test_db.query(Job).filter(Job.id == job_id).first()
        assert retrieved is not None
        assert retrieved.progress == 25.5
        assert retrieved.message == 'First 250 reviews ingested'

    def test_job_status_transition(self, test_db):
        """Test job status transitions"""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            job_type='ingest_reviews',
            status=JobStatus.QUEUED,
            app_ids=['test.app']
        )
        
        test_db.add(job)
        test_db.commit()
        
        # QUEUED -> PROCESSING
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        test_db.commit()
        
        retrieved = test_db.query(Job).filter(Job.id == job_id).first()
        assert retrieved.status == JobStatus.PROCESSING
        assert retrieved.started_at is not None

    def test_job_retry_increment(self, test_db):
        """Test retry count increments"""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            job_type='ingest_reviews',
            status=JobStatus.QUEUED,
            app_ids=['test.app'],
            retry_count=0,
            max_retries=3
        )
        
        test_db.add(job)
        test_db.commit()
        
        # Simulate retry
        job.retry_count += 1
        job.status = JobStatus.RETRYING
        job.message = 'Retry 1/3'
        test_db.commit()
        
        retrieved = test_db.query(Job).filter(Job.id == job_id).first()
        assert retrieved.retry_count == 1
        assert retrieved.status == JobStatus.RETRYING

    def test_job_max_retries_exceeded(self, test_db):
        """Test job failure when max retries exceeded"""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            job_type='ingest_reviews',
            status=JobStatus.RETRYING,
            app_ids=['test.app'],
            retry_count=3,
            max_retries=3
        )
        
        test_db.add(job)
        test_db.commit()
        
        # Exceed max retries
        if job.retry_count >= job.max_retries:
            job.status = JobStatus.FAILED
            job.error_message = 'Max retries exceeded'
        
        test_db.commit()
        
        retrieved = test_db.query(Job).filter(Job.id == job_id).first()
        assert retrieved.status == JobStatus.FAILED


class TestIngestReviewsSchema:
    """Tests for request/response schemas"""
    
    def test_ingest_request_valid(self):
        """Test valid ingest request"""
        request = IngestReviewsRequest(
            app_ids=['in.swiggy.android', 'com.application.zomato'],
            countries=['IN'],
            languages=['en'],
            max_reviews=500
        )
        
        assert request.app_ids == ['in.swiggy.android', 'com.application.zomato']
        assert request.max_reviews == 500

    def test_ingest_request_defaults(self):
        """Test ingest request with default values"""
        request = IngestReviewsRequest(
            app_ids=['test.app']
        )
        
        assert request.countries == ['IN']
        assert request.languages == ['en']
        assert request.max_reviews == 1000

    def test_ingest_response(self):
        """Test ingest response format"""
        response = IngestReviewsResponse(
            job_id='job-123',
            status='queued',
            app_ids=['in.swiggy.android'],
            created_at=datetime.utcnow()
        )
        
        assert response.job_id == 'job-123'
        assert response.status == 'queued'
        assert response.app_ids == ['in.swiggy.android']
