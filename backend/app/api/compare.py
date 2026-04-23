"""
Competitor Comparison API: Benchmark apps against each other
"""
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
import logging
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.models.review import Review, AspectSentiment
from app.models.insight import CompetitorComparison

logger = logging.getLogger(__name__)

router = APIRouter()


class CompareAppsRequest(BaseModel):
    apps: List[str]


@router.post("/aspects")
def compare_aspects(payload: CompareAppsRequest):
    """
    Compare sentiment across key aspects for multiple food-delivery apps
    """
    apps = payload.apps
    db = SessionLocal()
    try:
        if len(apps) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 apps to compare")
        
        comparison_data = {}
        
        for app_id in apps:
            aspect_data = {}
            
            # Get aspect sentiment distribution
            aspects = db.query(
                AspectSentiment.aspect,
                AspectSentiment.sentiment,
                func.count(AspectSentiment.id).label('count')
            ).join(
                Review, Review.id == AspectSentiment.review_id
            ).filter(
                Review.app_id == app_id,
                Review.is_spam == False
            ).group_by(
                AspectSentiment.aspect,
                AspectSentiment.sentiment
            ).all()
            
            for aspect, sentiment, count in aspects:
                if aspect not in aspect_data:
                    aspect_data[aspect] = {
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0,
                        'total': 0
                    }
                
                aspect_data[aspect][sentiment] += count
                aspect_data[aspect]['total'] += count
            
            # Calculate sentiment scores
            for aspect in aspect_data:
                total = aspect_data[aspect]['total']
                if total > 0:
                    # Weighted sentiment score
                    positive_weight = aspect_data[aspect]['positive'] / total
                    negative_weight = aspect_data[aspect]['negative'] / total
                    aspect_data[aspect]['sentiment_score'] = positive_weight - negative_weight
                    aspect_data[aspect]['positive_pct'] = positive_weight * 100
                    aspect_data[aspect]['negative_pct'] = negative_weight * 100
            
            comparison_data[app_id] = aspect_data
        
        # Create comparison matrix
        all_aspects = set()
        for app_data in comparison_data.values():
            all_aspects.update(app_data.keys())
        
        comparison_matrix = {}
        for aspect in all_aspects:
            comparison_matrix[aspect] = {
                app_id: comparison_data[app_id].get(aspect, {}).get('sentiment_score', 0)
                for app_id in apps
            }
        
        return {
            "apps": apps,
            "aspects_comparison": comparison_matrix,
            "detailed_data": comparison_data
        }
        
    finally:
        db.close()


@router.get("/sentiment")
def compare_overall_sentiment(apps: List[str] = Query(...)):
    """
    Compare overall sentiment scores and ratings across apps
    """
    db = SessionLocal()
    try:
        comparison = {}
        
        for app_id in apps:
            reviews = db.query(Review).filter(
                Review.app_id == app_id,
                Review.is_spam == False
            ).all()
            
            if not reviews:
                comparison[app_id] = None
                continue
            
            sentiments = [r.sentiment_score for r in reviews]
            ratings = [r.rating for r in reviews]
            sentiment_labels = [r.sentiment for r in reviews]
            
            comparison[app_id] = {
                'total_reviews': len(reviews),
                'avg_rating': sum(ratings) / len(ratings),
                'avg_sentiment_score': sum(sentiments) / len(sentiments),
                'rating_distribution': {
                    str(i): ratings.count(i) for i in range(1, 6)
                },
                'sentiment_distribution': {
                    'positive': sentiment_labels.count('positive'),
                    'negative': sentiment_labels.count('negative'),
                    'neutral': sentiment_labels.count('neutral')
                }
            }
        
        return {
            "apps": apps,
            "comparison": comparison
        }
        
    finally:
        db.close()


@router.get("/issues")
def compare_top_issues(apps: List[str] = Query(...), top_n: int = 5):
    """
    Compare top issues/complaints across competing apps
    """
    db = SessionLocal()
    try:
        issues_comparison = {}
        
        for app_id in apps:
            reviews = db.query(Review).filter(
                Review.app_id == app_id,
                Review.is_spam == False
            ).all()
            
            # Group by domain category
            category_freq = {}
            for review in reviews:
                category = review.domain_category
                if category not in category_freq:
                    category_freq[category] = {
                        'count': 0,
                        'negative_count': 0,
                        'avg_sentiment': 0
                    }
                
                category_freq[category]['count'] += 1
                if review.sentiment == 'negative':
                    category_freq[category]['negative_count'] += 1
            
            # Calculate metrics
            for category in category_freq:
                total = category_freq[category]['count']
                category_freq[category]['negative_pct'] = (
                    category_freq[category]['negative_count'] / total * 100
                )
            
            # Get top issues
            top_issues = sorted(
                category_freq.items(),
                key=lambda x: x[1]['negative_pct'],
                reverse=True
            )[:top_n]
            
            issues_comparison[app_id] = [
                {
                    'category': category,
                    'mention_count': data['count'],
                    'negative_mentions': data['negative_count'],
                    'negative_percentage': round(data['negative_pct'], 2)
                }
                for category, data in top_issues
            ]
        
        return {
            "apps": apps,
            "top_issues": issues_comparison,
            "top_n": top_n
        }
        
    finally:
        db.close()


@router.get("/feature-gap")
def identify_feature_gaps(primary_app: str = Query(...), competitor_apps: List[str] = Query(...)):
    """
    Identify features praised in competitors but missing in primary app
    """
    db = SessionLocal()
    try:
        # Get positive aspects mentioned in competitors
        competitor_strengths = set()
        
        for competitor_id in competitor_apps:
            aspects = db.query(
                AspectSentiment.aspect
            ).join(
                Review, Review.id == AspectSentiment.review_id
            ).filter(
                Review.app_id == competitor_id,
                AspectSentiment.sentiment == 'positive'
            ).distinct().all()
            
            competitor_strengths.update([a[0] for a in aspects])
        
        # Get negative aspects mentioned in primary app
        primary_weaknesses = set()
        
        aspects = db.query(
            AspectSentiment.aspect
        ).join(
            Review, Review.id == AspectSentiment.review_id
        ).filter(
            Review.app_id == primary_app,
            AspectSentiment.sentiment == 'negative'
        ).distinct().all()
        
        primary_weaknesses.update([a[0] for a in aspects])
        
        # Feature gaps = strong in competitors, weak in primary
        feature_gaps = competitor_strengths.intersection(primary_weaknesses)
        
        return {
            "primary_app": primary_app,
            "competitors": competitor_apps,
            "feature_gaps": list(feature_gaps),
            "recommendation": f"Consider improving {', '.join(feature_gaps) if feature_gaps else 'none identified'} to match competitor strengths"
        }
        
    finally:
        db.close()


@router.post("/")
def compare_apps(payload: dict):
    """
    Legacy endpoint: Compare multiple apps
    """
    if "apps" not in payload:
        raise HTTPException(status_code=400, detail="'apps' field required")
    
    apps = payload["apps"]
    
    if len(apps) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 apps to compare")
    
    return {
        "apps": apps,
        "comparison_generated": True,
        "use_endpoints": [
            "/compare/sentiment",
            "/compare/aspects",
            "/compare/issues",
            "/compare/feature-gap"
        ]
    }
