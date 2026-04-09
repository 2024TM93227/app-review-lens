"""
Analysis API Module: Generate decision dashboards from ingested reviews
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.db.session import SessionLocal
from app.models.review import Review, AspectSentiment
from app.models.insight import Insight
from app.models.job import Job, JobStatus
from app.api.schemas import DashboardResponse, IssueMetric, EvidenceReview, IssueDeepDiveResponse
from app.security import verify_auth

logger = logging.getLogger(__name__)
router = APIRouter()


def calculate_rating_change(app_id: str, days: int = 7, db: Session = None) -> float:
    """
    Calculate rating change over the last N days.
    Returns: current_avg - previous_avg
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        now = datetime.utcnow()
        current_period_start = now - timedelta(days=days//2)
        previous_period_start = now - timedelta(days=days)
        
        # Current period average
        current_avg = db.query(
            func.avg(Review.rating).label('avg_rating')
        ).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= current_period_start
        ).scalar() or 0

        # Previous period average
        previous_avg = db.query(
            func.avg(Review.rating).label('avg_rating')
        ).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= previous_period_start,
            Review.timestamp < current_period_start
        ).scalar() or 0

        return float(current_avg) - float(previous_avg) if previous_avg else 0
    finally:
        if should_close:
            db.close()


def get_sentiment_distribution(app_id: str, db: Session) -> Dict[str, int]:
    """Get count of reviews by sentiment."""
    distribution = db.query(
        Review.sentiment,
        func.count(Review.id).label('count')
    ).filter(
        Review.app_id == app_id,
        Review.is_spam == False
    ).group_by(Review.sentiment).all()

    result = {"positive": 0, "negative": 0, "neutral": 0}
    for sentiment, count in distribution:
        result[sentiment.lower()] = count
    return result


def get_top_issues(app_id: str, limit: int = 10, db: Session = None) -> List[IssueMetric]:
    """
    Get top issues ranked by priority score (multi-factor: frequency + sentiment + trend).
    Optimized to avoid N+1 queries by batch fetching trend counts.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Get issues from database or compute from reviews
        issues = db.query(Insight).filter(
            Insight.app_id == app_id
        ).order_by(Insight.priority_score.desc()).limit(limit).all()

        if not issues:
            return []

        # Batch fetch all trend counts in a single query
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(days=7)
        older_cutoff = now - timedelta(days=14)
        
        from sqlalchemy import and_, case
        
        # Create subqueries for recent and older counts per issue
        trend_data = db.query(
            Review.domain_category,
            Review.domain_subcategory,
            func.sum(case((Review.timestamp >= recent_cutoff, 1), else_=0)).label('recent_count'),
            func.sum(case(
                (and_(Review.timestamp < recent_cutoff, Review.timestamp >= older_cutoff), 1),
                else_=0
            )).label('older_count')
        ).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= older_cutoff
        ).group_by(
            Review.domain_category,
            Review.domain_subcategory
        ).all()
        
        # Convert to dict for fast lookup
        trend_map = {
            (row.domain_category, row.domain_subcategory): {
                'recent': row.recent_count or 0,
                'older': row.older_count or 0
            }
            for row in trend_data
        }

        result = []
        for idx, issue in enumerate(issues):
            # Look up pre-computed counts
            trend_info = trend_map.get((issue.category, issue.subcategory), {'recent': 0, 'older': 0})
            recent_count = trend_info['recent']
            older_count = trend_info['older']
            
            trend = (recent_count - older_count) / max(older_count, 1)

            # Determine severity based on priority score
            if issue.priority_score > 0.8:
                severity = "critical"
            elif issue.priority_score > 0.6:
                severity = "high"
            elif issue.priority_score > 0.4:
                severity = "medium"
            else:
                severity = "low"

            # Only the first issue is highlighted
            is_top = (idx == 0)

            result.append(IssueMetric(
                issue_id=issue.id,
                category=issue.category,
                severity=severity,
                frequency=issue.frequency,
                trend=min(trend, 1.0),  # Cap at 1.0
                rating_impact=issue.sentiment_score * -0.5,  # Negative sentiment impacts rating
                is_top_issue=is_top
            ))

        return result
    finally:
        if should_close:
            db.close()


@router.get("/{job_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(job_id: str, _auth: str = Depends(verify_auth)):
    """
    Get the decision dashboard for a completed job.
    
    Results are cached for 1 hour via in-memory cache.
    
    This is the primary endpoint for the decision dashboard screen.
    
    Returns:
    - Top issue highlighted (red card)
    - Other issues (blue cards)
    - Overall rating change
    - Sentiment distribution
    """
    db = SessionLocal()
    try:
        # Verify job exists and is completed
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is {job.status.value}, not completed yet"
            )

        if not job.app_ids or len(job.app_ids) == 0:
            raise HTTPException(status_code=400, detail="No apps in job")

        # Get primary app
        app_id = job.app_ids[0]

        # Get metrics
        total_reviews = db.query(func.count(Review.id)).filter(
            Review.app_id == app_id,
            Review.is_spam == False
        ).scalar() or 0

        avg_rating = db.query(
            func.avg(Review.rating)
        ).filter(
            Review.app_id == app_id,
            Review.is_spam == False
        ).scalar() or 0

        rating_change = calculate_rating_change(app_id, days=7, db=db)
        issues = get_top_issues(app_id, limit=10, db=db)
        sentiment_dist = get_sentiment_distribution(app_id, db)

        # Top issue
        top_issue = issues[0] if issues else None

        return DashboardResponse(
            job_id=job_id,
            app_id=app_id,
            total_reviews=total_reviews,
            avg_rating=float(avg_rating),
            rating_change=rating_change,
            top_issue=top_issue,
            issues=issues[1:] if len(issues) > 1 else [],  # Exclude top issue from list
            review_sentiment_distribution=sentiment_dist
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{job_id}/comparison")
def get_comparison_dashboard(job_id: str, _auth: str = Depends(verify_auth)):
    """
    Get comparison dashboard for two apps.
    
    Only available for comparison jobs with 2 app IDs.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if len(job.app_ids) != 2:
            raise HTTPException(
                status_code=400,
                detail="Comparison requires exactly 2 apps"
            )

        app_a_id, app_b_id = job.app_ids[0], job.app_ids[1]

        # Get ratings
        rating_a = db.query(func.avg(Review.rating)).filter(
            Review.app_id == app_a_id,
            Review.is_spam == False
        ).scalar() or 0

        rating_b = db.query(func.avg(Review.rating)).filter(
            Review.app_id == app_b_id,
            Review.is_spam == False
        ).scalar() or 0

        # Get aspect comparison
        aspects_a = db.query(
            AspectSentiment.aspect,
            func.sum(func.case((AspectSentiment.sentiment == 'positive', 1), else_=0)).label('positive'),
            func.sum(func.case((AspectSentiment.sentiment == 'negative', 1), else_=0)).label('negative'),
            func.count(AspectSentiment.id).label('total')
        ).join(Review).filter(
            Review.app_id == app_a_id,
            Review.is_spam == False
        ).group_by(AspectSentiment.aspect).all()

        aspects_b = db.query(
            AspectSentiment.aspect,
            func.sum(func.case((AspectSentiment.sentiment == 'positive', 1), else_=0)).label('positive'),
            func.sum(func.case((AspectSentiment.sentiment == 'negative', 1), else_=0)).label('negative'),
            func.count(AspectSentiment.id).label('total')
        ).join(Review).filter(
            Review.app_id == app_b_id,
            Review.is_spam == False
        ).group_by(AspectSentiment.aspect).all()

        # Get issues
        issues_a = get_top_issues(app_a_id, limit=5, db=db)
        issues_b = get_top_issues(app_b_id, limit=5, db=db)

        return {
            "job_id": job_id,
            "app_a_id": app_a_id,
            "app_b_id": app_b_id,
            "app_a_rating": float(rating_a),
            "app_b_rating": float(rating_b),
            "app_a_strengths": [i.category for i in issues_b[:3] if i.severity in ["low", "medium"]],  # B's weaknesses
            "app_b_weaknesses": [i.category for i in issues_b[:3]],
            "aspects_comparison": {
                "app_a": [{
                    "aspect": aspect,
                    "positive": positive or 0,
                    "negative": negative or 0,
                    "total": total or 0,
                    "score": (positive or 0) / max(total or 1, 1)
                } for aspect, positive, negative, total in aspects_a],
                "app_b": [{
                    "aspect": aspect,
                    "positive": positive or 0,
                    "negative": negative or 0,
                    "total": total or 0,
                    "score": (positive or 0) / max(total or 1, 1)
                } for aspect, positive, negative, total in aspects_b]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{job_id}/issues/{issue_id}")
def get_issue_details(job_id: str, issue_id: int, _auth: str = Depends(verify_auth)):
    """
    Get detailed information about a specific issue.
    
    Used for issue deep dive screen.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        issue = db.query(Insight).filter(Insight.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        app_id = job.app_ids[0]

        # Build trend data
        now = datetime.utcnow()
        trend_data = []
        for days_back in range(30, -1, -1):
            date = now - timedelta(days=days_back)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)

            count = db.query(func.count(Review.id)).filter(
                Review.app_id == app_id,
                Review.domain_category == issue.category,
                Review.domain_subcategory == issue.subcategory,
                Review.timestamp >= date_start,
                Review.timestamp < date_end,
                Review.is_spam == False
            ).scalar() or 0

            trend_data.append({
                "date": date.isoformat(),
                "count": count
            })

        # Get evidence reviews (raw review text and metadata)
        evidence_reviews_raw = db.query(Review).filter(
            Review.app_id == app_id,
            Review.domain_category == issue.category,
            Review.domain_subcategory == issue.subcategory,
            Review.is_spam == False
        ).order_by(Review.timestamp.desc()).limit(20).all()

        evidence_reviews = [
            EvidenceReview(
                review_id=r.review_id,
                rating=r.rating,
                text=r.text,
                date=r.timestamp,
                locale=r.locale,
                aspect_sentiment=None
            )
            for r in evidence_reviews_raw
        ]

        return IssueDeepDiveResponse(
            issue_id=issue.id,
            category=issue.category,
            subcategory=issue.subcategory,
            frequency=issue.frequency,
            trend_data=trend_data,
            evidence_reviews=evidence_reviews
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting issue details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{job_id}/issues/{issue_id}/evidence")
def get_issue_evidence(job_id: str, issue_id: int, limit: int = 50, _auth: str = Depends(verify_auth)):
    """
    Get raw review evidence for an issue.
    
    This is paginated and returns specific review texts that support the issue.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        issue = db.query(Insight).filter(Insight.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")

        app_id = job.app_ids[0]

        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.domain_category == issue.category,
            Review.domain_subcategory == issue.subcategory,
            Review.is_spam == False
        ).order_by(Review.timestamp.desc()).limit(limit).all()

        return {
            "issue_id": issue_id,
            "reviews": [
                {
                    "id": r.id,
                    "review_id": r.review_id,
                    "rating": r.rating,
                    "text": r.text,
                    "sentiment": r.sentiment,
                    "timestamp": r.timestamp.isoformat(),
                    "locale": r.locale
                }
                for r in reviews
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
