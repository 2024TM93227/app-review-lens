"""
Background Worker for Real-Time Review Collection
Periodically ingests reviews from Google Play Store using APScheduler
"""
import logging
from datetime import datetime
from typing import List

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    IntervalTrigger = None
    logging.warning("APScheduler not available - background worker disabled")

from app.services.playstore_scraper import fetch_reviews_incremental, validate_review, parse_review_date, normalize_review_for_storage
from app.services.nlp import (
    analyze_sentiment,
    extract_aspects,
    classify_domain_category,
    preprocess_text,
    detect_spam
)
from app.db.session import SessionLocal
from app.models.review import Review, AspectSentiment

logger = logging.getLogger(__name__)

# Apps to monitor for real-time ingestion
MONITORED_APPS = {
    'Swiggy': 'in.swiggy.deliveryapp',
    'Zomato': 'com.application.zomato',
    'Uber Eats': 'com.uber.restaurants',
    'DoorDash': 'com.dd.doordash',
}

scheduler = None


def ingest_app_reviews(app_id: str, app_name: str):
    """Ingest latest reviews for a single app (last 24 hours)"""
    db = SessionLocal()
    try:
        logger.info(f"[Background Worker] Starting real-time ingest for {app_name} ({app_id})")
        
        # Fetch reviews from last 1 day
        reviews_data = fetch_reviews_incremental(app_id, days=1)
        
        if not reviews_data:
            logger.debug(f"[Background Worker] No new reviews for {app_name}")
            return {"app": app_name, "ingested": 0}
        
        saved = 0
        for review_data in reviews_data:
            try:
                # Validate review
                if not validate_review(review_data):
                    continue
                
                text = review_data.get("content", "").strip()
                if len(text) < 10:
                    continue
                
                review_id = review_data.get('review_id')
                
                # Check for duplicates
                existing = db.query(Review).filter(Review.review_id == review_id).first()
                if existing:
                    continue
                
                # Preprocess text
                cleaned_text = preprocess_text(text)
                
                # Check spam
                is_spam = detect_spam(cleaned_text)
                
                # Analyze sentiment
                sentiment_label, sentiment_score = analyze_sentiment(cleaned_text)
                
                # Extract aspects
                aspects = extract_aspects(cleaned_text)
                
                # Classify domain category
                category, subcategory = classify_domain_category(cleaned_text)
                
                # Create Review record
                review = Review(
                    app_id=app_id,
                    review_id=review_id,
                    author=review_data.get("reviewer", "Unknown"),
                    rating=review_data.get("score", 3),
                    title=review_data.get("reviewTitle", ""),
                    content=text,
                    cleaned_content=cleaned_text,
                    sentiment_label=sentiment_label,
                    sentiment_score=sentiment_score,
                    aspects_json=aspects,
                    domain_category=category,
                    domain_subcategory=subcategory,
                    is_spam=is_spam,
                    review_date=parse_review_date(review_data.get('at', None)),
                    scraped_at=datetime.now(),
                    app_version=review_data.get('reviewCreatedVersion', 'Unknown'),
                    locale=review_data.get('locale', 'en_US'),
                    helpful_count=review_data.get('helpfulCount', 0),
                    raw_data=normalize_review_for_storage(review_data)
                )
                
                db.add(review)
                
                # Save aspect sentiment details
                for aspect, aspect_data in aspects.items():
                    aspect_sentiment = AspectSentiment(
                        review_id=review_id,
                        aspect_name=aspect,
                        aspect_sentiment=aspect_data.get('sentiment', 'neutral'),
                        aspect_confidence=aspect_data.get('confidence', 0.0),
                    )
                    db.add(aspect_sentiment)
                
                saved += 1
                
            except Exception as e:
                logger.warning(f"[Background Worker] Error processing review: {e}")
        
        db.commit()
        logger.info(f"[Background Worker] Saved {saved} new reviews for {app_name}")
        return {"app": app_name, "ingested": saved}
        
    except Exception as e:
        logger.error(f"[Background Worker] Error ingesting reviews for {app_name}: {e}")
        return {"app": app_name, "error": str(e)}
    finally:
        db.close()


def scheduled_real_time_ingest():
    """Background job that ingests reviews for all monitored apps"""
    logger.info("[Background Worker] Starting scheduled real-time ingest")
    results = []
    
    for app_name, app_id in MONITORED_APPS.items():
        result = ingest_app_reviews(app_id, app_name)
        results.append(result)
    
    logger.info(f"[Background Worker] Scheduled ingest completed: {results}")
    return results


def start_background_scheduler():
    """Initialize and start the background scheduler"""
    global scheduler

    if not APSCHEDULER_AVAILABLE:
        logger.warning("[Background Worker] APScheduler not available - skipping background scheduler")
        return

    if scheduler is not None:
        return

    try:
        scheduler = BackgroundScheduler()

        # Schedule real-time ingest every 30 minutes
        scheduler.add_job(
            scheduled_real_time_ingest,
            trigger=IntervalTrigger(minutes=30),
            id='real_time_ingest',
            name='Real-time review ingestion',
            replace_existing=True,
            misfire_grace_time=15,
        )

        scheduler.start()
        logger.info("[Background Worker] Background scheduler started - collecting reviews every 30 minutes")

    except Exception as e:
        logger.error(f"[Background Worker] Failed to start scheduler: {e}")


def stop_background_scheduler():
    """Stop the background scheduler"""
    global scheduler

    if not APSCHEDULER_AVAILABLE:
        return

    if scheduler is not None:
        try:
            scheduler.shutdown()
            scheduler = None
            logger.info("[Background Worker] Background scheduler stopped")
        except Exception as e:
            logger.error(f"[Background Worker] Error stopping scheduler: {e}")


def is_scheduler_running() -> bool:
    """Check if scheduler is running"""
    if not APSCHEDULER_AVAILABLE:
        return False
    return scheduler is not None and scheduler.running
