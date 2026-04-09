"""
Jobs API Module: Job queue management and status polling
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import uuid

from app.db.session import SessionLocal
from app.models.job import Job, JobStatus
from app.api.schemas import (
    IngestReviewsRequest,
    IngestReviewsResponse,
    JobStatusResponse
)
from app.security import verify_auth
from app.logging_utils import StructuredLogger
from app.services.playstore_scraper import (
    fetch_reviews,
    fetch_reviews_incremental,
    validate_review,
    parse_review_date,
    normalize_review_for_storage,
    generate_review_id
)
from app.services.nlp import (
    analyze_sentiment,
    extract_aspects,
    classify_domain_category,
    preprocess_text,
    detect_spam
)

logger = StructuredLogger(__name__)
router = APIRouter()


def process_ingest_job(job_id: str):
    """
    Background task: Process review ingestion for a job.
    Updates job status as it progresses.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.message = "Starting review ingestion..."
        db.commit()
        logger.info("job_ingestion_started", job_id=job_id, app_ids=job.app_ids)

        import time

        total_reviews_ingested = 0
        app_results = {}

        # Process each app
        for idx, app_id in enumerate(job.app_ids):
            try:
                        job.message = f"Ingesting reviews for {app_id}..."
                        db.commit()

                        # Fetch reviews incrementally (only new reviews since last ingestion)
                        since_date = job.last_ingested_timestamp if job.last_ingested_timestamp else job.since_date

                        fetch_start = time.time()
                        reviews_data = fetch_reviews_incremental(
                            app_id,
                            since_date=since_date,
                            max_reviews=job.max_reviews
                        )
                        fetch_elapsed = time.time() - fetch_start

                        if not reviews_data:
                            job.message = f"No new reviews found for {app_id}"
                            db.commit()
                            logger.info(f"No new reviews for {app_id} (fetch {fetch_elapsed:.2f}s)")
                            continue

                        saved = 0
                        app_results[app_id] = {"ingested": 0, "errors": 0, "fetch_time_s": fetch_elapsed}

                        # Use batch lists and bulk insert to reduce DB overhead
                        review_objects = []
                        aspect_objects = []

                        # sample timing for per-review processing
                        per_review_times = []

                        for i, review_data in enumerate(reviews_data, start=1):
                            try:
                                if not validate_review(review_data):
                                    continue

                                text = review_data.get("content", "").strip()
                                if len(text) < 10:
                                    continue

                                # Import Review model from reviews module to avoid circular imports
                                from app.models.review import Review

                                review_id = review_data.get("review_id")
                                # Parse timestamp safely with fallback to scraped_at or current time
                                parsed_timestamp = parse_review_date(review_data.get("at"))
                                if parsed_timestamp is None:
                                    scraped_at = review_data.get("scraped_at")
                                    timestamp = parse_review_date(scraped_at) if scraped_at else datetime.utcnow()
                                else:
                                    timestamp = parsed_timestamp

                                # Check if review already exists
                                existing = db.query(Review).filter(Review.review_id == review_id).first()
                                if existing:
                                    continue

                                # Process review (measure time)
                                t0 = time.time()
                                cleaned_text = preprocess_text(text)
                                is_spam = detect_spam(text)
                                sentiment_label, sentiment_score = analyze_sentiment(text)
                                aspects = extract_aspects(text)
                                domain_category, domain_subcategory = classify_domain_category(text)
                                t1 = time.time()
                                per_review_times.append(t1 - t0)

                                review_record = Review(
                                    app_id=app_id,
                                    review_id=review_id,
                                    rating=review_data.get("score", 3),
                                    text=text,
                                    cleaned_text=cleaned_text,
                                    author=review_data.get("userName"),
                                    locale=review_data.get("locale", "en_US"),
                                    sentiment=sentiment_label,
                                    sentiment_score=sentiment_score,
                                    aspects=aspects,
                                    domain_category=domain_category,
                                    domain_subcategory=domain_subcategory,
                                    is_spam=is_spam,
                                    is_processed=True,
                                    processing_status="processed",
                                    timestamp=timestamp
                                )

                                review_objects.append(review_record)

                                saved += 1

                                # Periodic progress update (less frequent)
                                if i % 200 == 0:
                                    job.reviews_ingested = total_reviews_ingested + saved
                                    job.progress = (idx + (saved / len(reviews_data))) / len(job.app_ids) * 100
                                    db.commit()

                            except Exception as e:
                                logger.error(f"Error processing review: {e}")
                                app_results[app_id]["errors"] += 1
                                continue

                        # Bulk save objects to reduce DB round-trips
                        if review_objects:
                            try:
                                db.bulk_save_objects(review_objects)
                                db.commit()
                            except Exception as e:
                                logger.error(f"Bulk insert failed for {app_id}: {e}")
                                # Fall back to individual adds on failure
                                for r in review_objects:
                                    db.add(r)
                                db.commit()

                        total_reviews_ingested += saved
                        app_results[app_id]["ingested"] = saved
                        app_results[app_id]["avg_review_proc_s"] = (sum(per_review_times) / len(per_review_times)) if per_review_times else 0
                        logger.info(f"Ingested {saved} reviews for {app_id} (fetch {fetch_elapsed:.2f}s, avg_proc {app_results[app_id]['avg_review_proc_s']:.3f}s)", app_id=app_id, count=saved)

            except Exception as e:
                logger.error(f"Error ingesting app {app_id}: {e}", app_id=app_id, error=str(e))
                app_results[app_id] = {"ingested": 0, "error": str(e)}
                continue

        # Successfully completed all apps - mark job as completed
        job.status = JobStatus.COMPLETED
        job.reviews_ingested = total_reviews_ingested
        job.progress = 100.0
        job.completed_at = datetime.utcnow()
        job.message = f"Ingestion complete: {total_reviews_ingested} reviews ingested"
        job.result_data = app_results
        db.commit()
        logger.info(f"Job {job_id} completed: {total_reviews_ingested} reviews ingested", job_id=job_id, results=app_results)

    except Exception as e:
        # Implement exponential backoff retry logic
        import time
        
        if job.retry_count < job.max_retries:
            # Calculate exponential backoff: 2^retry_count seconds
            backoff_seconds = 2 ** job.retry_count
            logger.warning(
                f"Job {job_id} failed: {e}. Retrying in {backoff_seconds}s ({job.retry_count + 1}/{job.max_retries})",
                job_id=job_id,
                retry_count=job.retry_count + 1,
                error=str(e)
            )
            
            job.status = JobStatus.RETRYING
            job.retry_count += 1
            job.last_retry_at = datetime.utcnow()
            job.message = f"Retry {job.retry_count} of {job.max_retries} - next attempt in {backoff_seconds}s"
            db.commit()
            db.close()
            
            # Wait then retry by recursing
            time.sleep(backoff_seconds)
            process_ingest_job(job_id)
        else:
            # Max retries exceeded
            logger.error(
                f"Job {job_id} failed permanently after {job.max_retries} retries: {e}",
                job_id=job_id,
                max_retries=job.max_retries
            )
            job.status = JobStatus.FAILED
            job.error_message = f"Failed after {job.max_retries} retries: {str(e)}"
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/ingest", response_model=IngestReviewsResponse)
def submit_ingest_job(request: IngestReviewsRequest, background_tasks: BackgroundTasks, _auth: str = Depends(verify_auth)):
    """
    Submit a background job to ingest reviews.
    
    Returns job ID for polling status.
    Client should poll GET /jobs/{job_id} to track progress.
    """
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    try:
        job = Job(
            id=job_id,
            job_type="ingest_reviews",
            status=JobStatus.QUEUED,
            app_ids=request.app_ids,
            countries=request.countries,
            languages=request.languages,
            since_date=request.since,
            until_date=request.until,
            max_reviews=request.max_reviews,
            message="Job queued, waiting to start"
        )
        db.add(job)
        db.commit()

        # Schedule background task
        background_tasks.add_task(process_ingest_job, job_id)

        return IngestReviewsResponse(
            job_id=job_id,
            status="queued",
            app_ids=request.app_ids,
            created_at=job.created_at
        )
    except Exception as e:
        logger.error(f"Error creating job: {e}", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """
    Poll job status by ID.
    
    Returns:
    - status: queued, processing, completed, failed
    - progress: 0-100
    - message: Human-readable status message
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(
            job_id=job.id,
            status=job.status.value,
            progress=job.progress,
            message=job.message or "In progress",
            created_at=job.created_at,
            completed_at=job.completed_at
        )
    finally:
        db.close()


@router.get("/{job_id}/result")
def get_job_result(job_id: str):
    """
    Get the final result of a completed job.
    
    Only available after job status is 'completed'.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is {job.status.value}, not completed yet"
            )

        return {
            "job_id": job.id,
            "status": job.status.value,
            "reviews_ingested": job.reviews_ingested,
            "result": job.result_data
        }
    finally:
        db.close()


@router.get("")
def list_jobs(status: str = None, limit: int = 50, skip: int = 0):
    """
    List jobs with optional filtering by status.
    
    Query params:
    - status: Filter by status (queued, processing, completed, failed, cancelled)
    - limit: Max results (default 50)
    - skip: Offset for pagination (default 0)
    """
    db = SessionLocal()
    try:
        query = db.query(Job).order_by(Job.created_at.desc())
        
        # Filter by status if provided
        if status:
            try:
                status_enum = JobStatus(status)
                query = query.filter(Job.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Must be one of: queued, processing, completed, failed, cancelled"
                )
        
        total = query.count()
        jobs = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "limit": limit,
            "skip": skip,
            "jobs": [
                {
                    "job_id": job.id,
                    "status": job.status.value,
                    "priority": job.priority,
                    "progress": job.progress,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "message": job.message
                }
                for job in jobs
            ]
        }
    finally:
        db.close()


@router.delete("/{job_id}")
def cancel_job(job_id: str, _auth: str = Depends(verify_auth)):
    """
    Cancel a running or queued job.
    
    Returns error if job is already completed or failed.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Only allow cancellation of queued or processing jobs
        if job.status not in [JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.RETRYING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status '{job.status.value}'"
            )
        
        # Mark job as cancelled
        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.utcnow()
        job.message = "Job cancelled by user"
        db.commit()
        
        logger.info(f"Job {job_id} cancelled", job_id=job_id, previous_status=job.status.value)
        
        return {
            "job_id": job.id,
            "status": job.status.value,
            "cancelled_at": job.cancelled_at,
            "message": "Job successfully cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error cancelling job: {str(e)}")
    finally:
        db.close()


@router.patch("/{job_id}/priority")
def update_job_priority(job_id: str, priority: int, _auth: str = Depends(verify_auth)):
    """
    Update job priority (1-10, higher = more urgent).
    
    Only allows updating priority for queued jobs.
    """
    db = SessionLocal()
    try:
        # Validate priority range
        if priority < 1 or priority > 10:
            raise HTTPException(
                status_code=400,
                detail="Priority must be between 1 and 10"
            )
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Only allow priority updates for queued jobs
        if job.status != JobStatus.QUEUED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update priority for job with status '{job.status.value}'"
            )
        
        old_priority = job.priority
        job.priority = priority
        db.commit()
        
        logger.info(
            f"Job {job_id} priority updated",
            job_id=job_id,
            old_priority=old_priority,
            new_priority=priority
        )
        
        return {
            "job_id": job.id,
            "priority": job.priority,
            "message": f"Priority updated from {old_priority} to {priority}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job priority: {e}", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error updating job priority: {str(e)}")
    finally:
        db.close()
