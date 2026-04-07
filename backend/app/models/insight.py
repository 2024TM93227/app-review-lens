from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from datetime import datetime


def current_time():
    return datetime.now()
from app.db.base import Base


class Insight(Base):
    """Aggregated insights for product managers"""
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True)
    app_id = Column(String, index=True)
    
    # Classification
    category = Column(String)  # Delivery, Order, Payments, App, Support, Offers
    subcategory = Column(String)  # Delay, Accuracy, Crash, etc.
    issue_description = Column(Text)  # Summary of the issue
    
    # Metrics
    frequency = Column(Integer)  # Number of reviews mentioning this issue
    sentiment_score = Column(Float)  # Average sentiment score
    rating_delta = Column(Float)  # Difference in average rating
    
    # Prioritization
    priority_score = Column(Float)  # Composite severity score
    rank = Column(Integer, index=True)  # Ranking for this app
    
    # Time Series
    created_at = Column(DateTime, default=current_time, index=True)
    updated_at = Column(DateTime, default=current_time, onupdate=current_time)
    last_seen = Column(DateTime)  # When was this issue last mentioned
    first_seen = Column(DateTime)  # When was this issue first mentioned
    
    # Evidence & Auditability
    sample_reviews = Column(JSON)  # List of review IDs for audit trail
    evidence_snippets = Column(JSON)  # Quote samples from reviews
    
    # Metadata
    release_version = Column(String, nullable=True)  # Which app version introduced this issue
    affected_regions = Column(JSON, nullable=True)  # ["IN", "US", "UK"]
    
    # Action Status
    status = Column(String, default="new")  # new, acknowledged, in_progress, resolved
    pm_notes = Column(Text, nullable=True)


class CompetitorComparison(Base):
    """Competitor benchmarking data"""
    __tablename__ = "competitor_comparisons"
    
    id = Column(Integer, primary_key=True)
    app_id = Column(String, index=True)
    competitor_app_id = Column(String, index=True)
    
    # Aspect-level Comparison
    aspect = Column(String, index=True)  # delivery_time, order_accuracy, etc.
    app_sentiment_score = Column(Float)
    competitor_sentiment_score = Column(Float)
    sentiment_gap = Column(Float)  # negative = competitor better
    
    # Volume Normalization
    app_issue_rate = Column(Float)  # % of reviews mentioning this issue
    competitor_issue_rate = Column(Float)
    rate_difference = Column(Float)
    
    # Ranking
    app_rank = Column(Integer)  # 1 = best, higher = worse
    comparison_date = Column(DateTime, default=current_time, index=True)


class ReleaseImpact(Base):
    """Track impact of app releases on review sentiment"""
    __tablename__ = "release_impacts"
    
    id = Column(Integer, primary_key=True)
    app_id = Column(String, index=True)
    version = Column(String, index=True)
    release_date = Column(DateTime, index=True)
    
    # Sentiment Impact
    pre_release_sentiment = Column(Float)  # Average sentiment before release
    post_release_sentiment = Column(Float)  # Average sentiment after release
    sentiment_change = Column(Float)  # Delta
    
    # Volume Impact
    pre_release_volume = Column(Integer)  # Reviews in 7 days before
    post_release_volume = Column(Integer)  # Reviews in 7 days after
    
    # Issue Emergence
    new_issues = Column(JSON)  # [{"category": "Crashes", "frequency": 5}, ...]
    resolved_issues = Column(JSON)
    
    # Analysis
    conclusion = Column(Text, nullable=True)  # PM-friendly summary
    recommendations = Column(JSON, nullable=True)  # ["Investigate crash on v2.1", ...]


class AnomalyAlert(Base):
    """Detected anomalies for PM attention"""
    __tablename__ = "anomaly_alerts"
    
    id = Column(Integer, primary_key=True)
    app_id = Column(String, index=True)
    
    alert_type = Column(String)  # sentiment_spike, issue_burst, crash_pattern, competitor_threat
    description = Column(Text)
    severity = Column(String)  # critical, high, medium, low
    
    # Detection Details
    baseline_value = Column(Float)
    detected_value = Column(Float)
    change_percentage = Column(Float)
    
    affected_aspect = Column(String, nullable=True)
    affected_region = Column(String, nullable=True)
    
    detected_at = Column(DateTime, default=current_time, index=True)
    created_at = Column(DateTime, default=current_time)
    
    # Action Tracking
    acknowledged = Column(String, default="pending")  # pending, acknowledged, resolved
    pm_response = Column(Text, nullable=True)
