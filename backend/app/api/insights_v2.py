"""
V2 Insights API: Enhanced endpoints for PM-focused dashboard
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.db.session import SessionLocal
from app.models.review import Review
from app.services.classification import classify_issue, get_all_categories
from app.services.severity import calculate_severity
from app.services.prioritization import aggregate_issues
from app.services.alerts import detect_alerts
from app.services.trends import build_sentiment_trend

logger = logging.getLogger(__name__)

router = APIRouter()


def _review_to_dict(r) -> dict:
    """Convert a Review ORM object to a plain dict for service functions."""
    return {
        "id": r.id,
        "review_id": r.review_id,
        "app_id": r.app_id,
        "rating": r.rating,
        "text": r.text,
        "sentiment": r.sentiment,
        "sentiment_score": r.sentiment_score,
        "domain_category": r.domain_category,
        "domain_subcategory": r.domain_subcategory,
        "issue_category": classify_issue(r.text or ""),
        "timestamp": r.timestamp,
        "app_version": r.app_version,
    }


@router.get("/{app_id}")
def get_insights_v2(app_id: str, days: int = 30):
    """
    GET /v2/insights/{app_id}
    Returns top_issues (prioritized), alerts, and rating_trend.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= cutoff,
        ).all()

        if not reviews:
            return {
                "app_id": app_id,
                "top_issues": [],
                "alerts": [],
                "rating_trend": [],
                "total_reviews": 0,
            }

        review_dicts = [_review_to_dict(r) for r in reviews]

        # Prioritized issues
        top_issues = aggregate_issues(review_dicts)

        # Alerts (spike detection)
        alerts = detect_alerts(review_dicts)

        # Rating trend (daily)
        rating_trend = _build_rating_trend(review_dicts)

        return {
            "app_id": app_id,
            "total_reviews": len(reviews),
            "top_issues": top_issues,
            "alerts": alerts,
            "rating_trend": rating_trend,
        }

    except Exception as e:
        logger.exception("Error in get_insights_v2")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{app_id}/issues/{issue_name}")
def get_issue_detail(app_id: str, issue_name: str, days: int = 30):
    """
    GET /v2/insights/{app_id}/issues/{issue_name}
    Returns detailed stats, sentiment breakdown, and filtered reviews for a specific issue.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= cutoff,
        ).all()

        if not reviews:
            raise HTTPException(status_code=404, detail="No reviews found")

        total_all = len(reviews)
        review_dicts = [_review_to_dict(r) for r in reviews]

        # Filter to this issue
        issue_reviews = [r for r in review_dicts if r["issue_category"] == issue_name]

        if not issue_reviews:
            raise HTTPException(status_code=404, detail=f"No reviews found for issue '{issue_name}'")

        freq = len(issue_reviews)
        sentiments = [r["sentiment_score"] for r in issue_reviews]
        ratings = [r["rating"] for r in issue_reviews]
        severities = [
            calculate_severity(r["rating"], r["sentiment_score"], r["text"])
            for r in issue_reviews
        ]

        sentiment_breakdown = {
            "positive": sum(1 for r in issue_reviews if r["sentiment"] == "positive"),
            "negative": sum(1 for r in issue_reviews if r["sentiment"] == "negative"),
            "neutral": sum(1 for r in issue_reviews if r["sentiment"] == "neutral"),
        }

        # Trend chart for this issue
        trend_data = build_sentiment_trend(issue_reviews, bucket="daily")

        # AI insight (template-based)
        ai_insight = _generate_issue_insight(issue_name, issue_reviews, freq, total_all)

        return {
            "issue_name": issue_name,
            "app_id": app_id,
            "frequency": freq,
            "affected_users_pct": round((freq / total_all) * 100, 1),
            "avg_rating": round(sum(ratings) / freq, 2),
            "avg_sentiment": round(sum(sentiments) / freq, 3),
            "avg_severity": round(sum(severities) / freq, 2),
            "sentiment_breakdown": sentiment_breakdown,
            "trend_data": trend_data,
            "ai_insight": ai_insight,
            "reviews": [
                {
                    "text": r["text"],
                    "rating": r["rating"],
                    "sentiment": r["sentiment"],
                    "sentiment_score": r["sentiment_score"],
                    "timestamp": r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else r["timestamp"],
                    "app_version": r.get("app_version"),
                    "severity": calculate_severity(r["rating"], r["sentiment_score"], r["text"]),
                }
                for r in sorted(issue_reviews, key=lambda x: x.get("sentiment_score", 1))[:50]
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in get_issue_detail")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{app_id}/alerts")
def get_alerts(app_id: str, days: int = 14):
    """
    GET /v2/insights/{app_id}/alerts
    Returns detected alert spikes.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=days)
        reviews = db.query(Review).filter(
            Review.app_id == app_id,
            Review.is_spam == False,
            Review.timestamp >= cutoff,
        ).all()

        review_dicts = [_review_to_dict(r) for r in reviews]
        alerts = detect_alerts(review_dicts)

        return {"app_id": app_id, "alerts": alerts}
    except Exception as e:
        logger.exception("Error in get_alerts")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


def _build_rating_trend(reviews: list) -> list:
    """Build daily average rating trend."""
    from collections import defaultdict

    daily = defaultdict(list)
    for r in reviews:
        ts = r.get("timestamp")
        if not ts:
            continue
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        day = ts.strftime("%Y-%m-%d")
        daily[day].append(r.get("rating", 3))

    trend = []
    for day in sorted(daily.keys()):
        ratings = daily[day]
        trend.append({
            "date": day,
            "avg_rating": round(sum(ratings) / len(ratings), 2),
            "count": len(ratings),
        })
    return trend


def _generate_issue_insight(issue_name: str, reviews: list, freq: int, total: int) -> str:
    """Generate a template-based AI insight string for an issue."""
    pct = round((freq / total) * 100, 1) if total else 0
    neg_count = sum(1 for r in reviews if r.get("sentiment") == "negative")
    avg_rating = sum(r.get("rating", 3) for r in reviews) / freq if freq else 3

    label = issue_name.replace("_", " ").title()

    # Check for version clustering
    versions = [r.get("app_version") for r in reviews if r.get("app_version")]
    version_note = ""
    if versions:
        from collections import Counter
        top_version = Counter(versions).most_common(1)
        if top_version:
            v, c = top_version[0]
            if c > freq * 0.3:
                version_note = f" Complaints are concentrated around version {v}."

    if avg_rating < 2:
        tone = "Users are strongly dissatisfied"
    elif avg_rating < 3:
        tone = "Users are reporting frequent issues"
    else:
        tone = "Some users are mentioning concerns"

    return (
        f"{tone} with {label.lower()}, affecting {pct}% of reviews. "
        f"{neg_count} out of {freq} mentions are negative with an average rating of {avg_rating:.1f}.{version_note}"
    )
