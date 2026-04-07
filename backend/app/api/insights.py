"""
Insights API Module: Generate and serve actionable insights for PMs
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.db.session import SessionLocal
from app.models.review import Review, AspectSentiment
from app.models.insight import Insight, ReleaseImpact, AnomalyAlert
from app.services.prioritization import (
    calculate_priority_score,
    rank_issues,
    calculate_issue_metrics,
    detect_sentiment_spikes,
    calculate_release_impact
)
from app.services.trends import (
    build_sentiment_trend,
    detect_change_points,
    identify_emerging_issues
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{app_id}")
def get_insights(app_id: str):
    """
    Get comprehensive insights for an app
    """
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False
        ).all()
        
        if not reviews:
            return {
                "app_id": app_id,
                "error": "No reviews found"
            }
        
        # Get top issues by priority
        insights = db.query(Insight).filter(
            Insight.app_id == app_id
        ).order_by(Insight.priority_score.desc()).limit(10).all()
        
        return {
            "app_id": app_id,
            "total_reviews": len(reviews),
            "insights": [
                {
                    "id": i.id,
                    "category": i.category,
                    "subcategory": i.subcategory,
                    "description": i.issue_description,
                    "frequency": i.frequency,
                    "priority_score": i.priority_score,
                    "rank": i.rank,
                    "sentiment_score": i.sentiment_score,
                    "status": i.status,
                    "last_seen": i.last_seen.isoformat() if i.last_seen else None
                }
                for i in insights
            ]
        }
    finally:
        db.close()


@router.post("/generate/{app_id}")
def generate_insights(app_id: str):
    """
    Generate insights from reviews (should be called periodically)
    Analyzes domain categories, aspects, and computes priority scores
    """
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.is_processed == True
        ).all()
        logger.info(f"Generate insights: found {len(reviews)} processed reviews for {app_id}")
        
        if not reviews:
            raise HTTPException(status_code=404, detail="No processed reviews found")
        
        # Group by domain category and subcategory
        category_issues = {}
        
        for review in reviews:
            key = (review.domain_category, review.domain_subcategory)
            if key not in category_issues:
                category_issues[key] = {
                    'reviews': [],
                    'frequency': 0,
                    'ratings': [],
                    'sentiments': []
                }
            
            category_issues[key]['reviews'].append(review)
            category_issues[key]['frequency'] += 1
            category_issues[key]['ratings'].append(review.rating)
            category_issues[key]['sentiments'].append(review.sentiment_score)
        
        # Generate insights
        generated_count = 0
        for (category, subcategory), data in category_issues.items():

            
            # Calculate metrics
            avg_sentiment = sum(data['sentiments']) / len(data['sentiments']) if data['sentiments'] else 0.5
            avg_rating = sum(data['ratings']) / len(data['ratings']) if data['ratings'] else 3
            rating_delta = avg_rating - 3.0  # Baseline 3-star
            
            # Calculate priority score
            priority_score = calculate_priority_score(
                frequency=data['frequency'],
                sentiment_score=avg_sentiment,
                rating=avg_rating,
                days_old=0
            )
            
            # Check if insight already exists
            existing = db.query(Insight).filter(
                Insight.app_id == app_id,
                Insight.category == category,
                Insight.subcategory == subcategory
            ).first()
            
            if existing:
                # Update existing insight
                existing.frequency = data['frequency']
                existing.sentiment_score = avg_sentiment
                existing.rating_delta = rating_delta
                existing.priority_score = priority_score
                existing.updated_at = datetime.now()
                existing.last_seen = datetime.now()
            else:
                # Create new insight
                insight = Insight(
                    app_id=app_id,
                    category=category,
                    subcategory=subcategory,
                    issue_description=f"{category}: {subcategory}",
                    frequency=data['frequency'],
                    sentiment_score=avg_sentiment,
                    rating_delta=rating_delta,
                    priority_score=priority_score,
                    sample_reviews=[r.review_id for r in data['reviews'][:5]],
                    status="new",
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
                db.add(insight)
            
            generated_count += 1
        
        db.commit()
        logger.info(f"Generated {generated_count} insights for {app_id}")
        
        return {
            "app_id": app_id,
            "insights_generated": generated_count
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error generating insights:")
        detail = str(e) or "Internal server error"
        raise HTTPException(status_code=500, detail=detail)
    finally:
        db.close()


@router.get("/{app_id}/top-issues")
def get_top_issues(app_id: str, limit: int = 10):
    """Get ranked list of top issues by priority"""
    db = SessionLocal()
    try:
        insights = db.query(Insight).filter(
            Insight.app_id == app_id
        ).order_by(Insight.priority_score.desc()).limit(limit).all()
        
        return {
            "app_id": app_id,
            "total_issues": len(insights),
            "issues": [
                {
                    "rank": idx + 1,
                    "category": i.category,
                    "subcategory": i.subcategory,
                    "priority_score": round(i.priority_score, 2),
                    "frequency": i.frequency,
                    "avg_sentiment": round(i.sentiment_score, 2),
                    "avg_rating_impact": round(i.rating_delta, 2),
                    "status": i.status
                }
                for idx, i in enumerate(insights)
            ]
        }
    finally:
        db.close()


@router.get("/{app_id}/anomalies")
def get_anomalies(app_id: str):
    """Get detected anomalies and unusual patterns"""
    db = SessionLocal()
    try:
        alerts = db.query(AnomalyAlert).filter(
            AnomalyAlert.app_id == app_id,
            AnomalyAlert.acknowledged == "pending"
        ).order_by(AnomalyAlert.detected_at.desc()).limit(20).all()
        
        return {
            "app_id": app_id,
            "anomalies": [
                {
                    "type": a.alert_type,
                    "description": a.description,
                    "severity": a.severity,
                    "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                    "change_percentage": round(a.change_percentage, 2),
                    "affected_aspect": a.affected_aspect
                }
                for a in alerts
            ]
        }
    finally:
        db.close()


@router.get("/{app_id}/emerging-issues")
def get_emerging_issues(app_id: str, days: int = 7):
    """Identify new issues that weren't mentioned before"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= cutoff_date
        ).all()
        
        if not reviews:
            return {"error": "No recent reviews found"}
        
        emerging = identify_emerging_issues(
            [
                {
                    'content': r.text,
                    'timestamp': r.timestamp.isoformat() if r.timestamp else None,
                }
                for r in reviews
            ]
        )
        
        return {
            "app_id": app_id,
            "period_days": days,
            "emerging_issues": emerging
        }
    finally:
        db.close()


@router.post("/{app_id}/release-impact")
def analyze_release_impact(
    app_id: str,
    version: str,
    release_date: str,
    pre_window_days: int = 7,
    post_window_days: int = 7
):
    """
    Analyze the impact of a release on review sentiment and issues
    """
    db = SessionLocal()
    try:
        release_datetime = datetime.fromisoformat(release_date)
        
        # Get reviews before and after release
        reviews_before = db.query(Review).filter(
            Review.app_id == app_id,
            Review.timestamp >= release_datetime - timedelta(days=pre_window_days),
            Review.timestamp < release_datetime
        ).all()
        
        reviews_after = db.query(Review).filter(
            Review.app_id == app_id,
            Review.timestamp >= release_datetime,
            Review.timestamp <= release_datetime + timedelta(days=post_window_days)
        ).all()
        
        # Calculate impact
        impact = calculate_release_impact(
            [
                {
                    'sentiment_score': r.sentiment_score,
                    'rating': r.rating,
                    'timestamp': r.timestamp
                }
                for r in reviews_before
            ],
            [
                {
                    'sentiment_score': r.sentiment_score,
                    'rating': r.rating,
                    'timestamp': r.timestamp
                }
                for r in reviews_after
            ]
        )
        
        # Store in database
        release_record = ReleaseImpact(
            app_id=app_id,
            version=version,
            release_date=release_datetime,
            pre_release_sentiment=impact['before'].get('avg_sentiment', 0),
            post_release_sentiment=impact['after'].get('avg_sentiment', 0),
            sentiment_change=impact['sentiment_change'],
            pre_release_volume=impact['before'].get('volume', 0),
            post_release_volume=impact['after'].get('volume', 0),
            conclusion=f"Release {version} resulted in {impact['status']} sentiment trend"
        )
        db.add(release_record)
        db.commit()
        
        return {
            "version": version,
            "release_date": release_date,
            "impact": impact
        }
        
    finally:
        db.close()

    sentiment_trend = build_sentiment_trend(enriched_reviews)

    return {
        "app_id": app_id,
        "total_reviews": len(enriched_reviews),
        "sentiment_trend": sentiment_trend
    }
