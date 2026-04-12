"""
Reviews API Module: Ingest and retrieve reviews with comprehensive processing
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.services.playstore_scraper import fetch_reviews, validate_review, parse_review_date, normalize_review_for_storage
from app.services.nlp import (
    analyze_sentiment,
    extract_aspects,
    classify_domain_category,
    preprocess_text,
    detect_spam
)
from app.services.classification import classify_issue
from app.services.sentiment import analyze_sentiment_v2
from app.services.severity import calculate_severity
from app.services.preprocessing import preprocess_review
from app.db.session import SessionLocal
from app.models.review import Review, AspectSentiment
from app.services.trends import build_sentiment_trend

logger = logging.getLogger(__name__)
router = APIRouter()


# ==============================
# INGEST REVIEWS (FIXED)
# ==============================
@router.post("/ingest/{app_id}")
def ingest_reviews(app_id: str, country: str = "in", lang: str = "en", count: int = 300):
    db = SessionLocal()
    try:
        logger.info(f"Starting ingestion for {app_id}")

        # 🔥 Fetch newest reviews
        reviews_data, _ = fetch_reviews(
            app_id,
            country=country,
            lang=lang,
            count=count,  # IMPORTANT FIX
        )

        if not reviews_data:
            return {"ingested": 0, "error": "No reviews found"}

        saved = 0
        updated = 0

        for review_data in reviews_data:
            try:
                if not validate_review(review_data):
                    continue

                text = review_data.get("content", "").strip()
                if len(text) < 3:
                    continue

                review_id = review_data.get("review_id")
                timestamp = parse_review_date(review_data.get("at"))

                existing = db.query(Review).filter(Review.review_id == review_id).first()

                # 🔥 UPDATE EXISTING (instead of skipping)
                if existing:
                    existing.text = text
                    existing.sentiment, existing.sentiment_score = analyze_sentiment_v2(text, rating=existing.rating)
                    existing.issue_category = classify_issue(text)
                    existing.severity = calculate_severity(existing.rating or 3, existing.sentiment_score, text)
                    existing.timestamp = timestamp
                    updated += 1
                    continue

                # New review processing
                cleaned_text = preprocess_text(text)
                preprocessed_text = preprocess_review(text)
                is_spam = detect_spam(text)
                sentiment_label, sentiment_score = analyze_sentiment_v2(text, rating=review_data.get("score"))
                aspects = extract_aspects(text)
                domain_category, domain_subcategory = classify_domain_category(text)
                issue_category = classify_issue(text)
                severity_score = calculate_severity(review_data.get("score", 3), sentiment_score, text)

                review_record = Review(
                    app_id=app_id,
                    review_id=review_id,
                    rating=review_data.get("score"),
                    text=text,
                    cleaned_text=cleaned_text,
                    author=review_data.get("userName"),
                    app_version=review_data.get("reviewCreatedVersion"),
                    locale=f"{lang}_{country.upper()}",
                    device_info=review_data.get("device"),
                    timestamp=timestamp,
                    sentiment=sentiment_label,
                    sentiment_score=sentiment_score,
                    aspects=aspects,
                    domain_category=domain_category,
                    domain_subcategory=domain_subcategory,
                    issue_category=issue_category,
                    severity=severity_score,
                    is_spam=is_spam,
                    is_processed=True,
                    processing_status="processed",
                    raw_data=normalize_review_for_storage(review_data)
                )

                db.add(review_record)
                db.flush()

                # Save aspect sentiment
                for aspect, aspect_sentiment in aspects.items():
                    db.add(AspectSentiment(
                        review_id=review_record.id,
                        aspect=aspect,
                        sentiment=aspect_sentiment,
                        confidence=0.8,
                        evidence_text=text[:100]
                    ))

                saved += 1

            except Exception as e:
                logger.error(f"Error processing review: {e}")
                continue

        db.commit()

        return {
            "ingested": saved,
            "updated": updated,
            "total_fetched": len(reviews_data),
            "app_id": app_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ==============================
# LIST REVIEWS (LATEST FIRST)
# ==============================
@router.get("/app/{app_id}/list")
def list_reviews(
    app_id: str,
    sentiment: Optional[str] = None,
    issue_category: Optional[str] = None,
    rating: Optional[int] = None,
    days: Optional[int] = None,
    is_spam: bool = False,
    limit: int = 50,
    offset: int = 0
):
    db = SessionLocal()
    try:
        query = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == is_spam
        )

        if issue_category:
            query = query.filter(Review.issue_category == issue_category)
        if rating:
            query = query.filter(Review.rating == rating)
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(Review.timestamp >= cutoff)

        # Fetch all matching reviews (before sentiment filter) so we can
        # re-derive sentiment with rating-aware logic, then apply sentiment filter
        all_reviews = query.order_by(Review.timestamp.desc()).all()

        def _corrected_review(r):
            label, score = analyze_sentiment_v2(r.text or "", rating=r.rating)
            return {
                "id": r.id,
                "rating": r.rating,
                "text": r.text,
                "sentiment": label,
                "sentiment_score": score,
                "issue_category": r.issue_category,
                "severity": r.severity,
                "app_version": r.app_version,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None
            }

        corrected = [_corrected_review(r) for r in all_reviews]

        # Apply sentiment filter on corrected labels (not stale DB values)
        if sentiment:
            corrected = [r for r in corrected if r["sentiment"] == sentiment]

        total = len(corrected)
        paginated = corrected[offset:offset + limit]

        return {
            "total": total,
            "reviews": paginated
        }
    finally:
        db.close()


# ==============================
# STATS
# ==============================
@router.get("/app/{app_id}/stats")
def get_review_stats(app_id: str):
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False
        ).all()

        if not reviews:
            return {"error": "No reviews found"}

        ratings = [r.rating for r in reviews]
        sentiments = [r.sentiment for r in reviews]
        scores = [r.sentiment_score for r in reviews]

        return {
            "total_reviews": len(reviews),
            "avg_rating": sum(ratings) / len(ratings),
            "avg_sentiment_score": sum(scores) / len(scores),
            "sentiment_distribution": {
                "positive": sentiments.count("positive"),
                "negative": sentiments.count("negative"),
                "neutral": sentiments.count("neutral")
            }
        }
    finally:
        db.close()


# ==============================
# TRENDS
# ==============================
@router.get("/app/{app_id}/trends")
def get_sentiment_trends(app_id: str, days: int = 30):
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)

        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.timestamp >= cutoff,
            Review.is_spam == False
        ).all()

        if not reviews:
            return {"error": "No recent reviews"}

        trend_data = build_sentiment_trend(
            [{
                "timestamp": r.timestamp,
                "sentiment_score": r.sentiment_score
            } for r in reviews],
            bucket="daily"
        )

        return {
            "trend_data": trend_data
        }

    finally:
        db.close()