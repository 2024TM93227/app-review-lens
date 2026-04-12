from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text
from datetime import datetime


def current_time():
    return datetime.now()
from app.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    app_id = Column(String, index=True)
    review_id = Column(String, unique=True, index=True)  # Google Play Store review ID
    rating = Column(Integer)  # 1-5 stars
    text = Column(Text)
    cleaned_text = Column(Text, nullable=True)
    author = Column(String, nullable=True)
    
    # Metadata
    app_version = Column(String, nullable=True)
    locale = Column(String, default="en_US", index=True)
    device_info = Column(String, nullable=True)
    timestamp = Column(DateTime, default=current_time, index=True)
    scraped_at = Column(DateTime, default=current_time)
    
    # Sentiment Analysis
    sentiment = Column(String)  # positive, negative, neutral
    sentiment_score = Column(Float)  # 0-1
    
    # Aspect Extraction
    aspects = Column(JSON, nullable=True)  # {"delivery_time": "negative", "ui_ux": "positive", ...}
    
    # Topic & Domain Classification
    topic = Column(String, nullable=True)
    domain_category = Column(String, nullable=True)  # Delivery, Order, Payments, App, Support
    domain_subcategory = Column(String, nullable=True)  # Delay, Accuracy, Crash, etc.
    issue_category = Column(String, nullable=True, index=True)  # V2: delivery_time, food_quality, etc.
    severity = Column(Float, nullable=True)  # V2: severity score 0-10
    
    # Embeddings & Clustering
    embedding = Column(JSON, nullable=True)  # Vector for similarity/clustering
    cluster_id = Column(Integer, nullable=True, index=True)
    
    # Quality Flags
    is_spam = Column(Boolean, default=False, index=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, nullable=True)  # Reference to original review
    
    # Audit & Traceability
    is_processed = Column(Boolean, default=False, index=True)
    processing_status = Column(String, default="pending")  # pending, processed, error
    raw_data = Column(JSON, nullable=True)  # Original Play Store data


class AspectSentiment(Base):
    """Extracted aspects and their sentiments for each review"""
    __tablename__ = "aspect_sentiments"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, index=True)
    aspect = Column(String, index=True)  # delivery_time, order_accuracy, tracking, ui_ux, payment, support, offers
    sentiment = Column(String)  # positive, negative, neutral
    confidence = Column(Float)  # 0-1
    evidence_text = Column(String, nullable=True)  # Quote from review supporting this aspect


class ReviewTrend(Base):
    """Aggregated trends by aspect and time period"""
    __tablename__ = "review_trends"
    
    id = Column(Integer, primary_key=True)
    app_id = Column(String, index=True)
    aspect = Column(String, index=True)
    date_bucket = Column(DateTime, index=True)  # Daily/Weekly aggregation
    avg_sentiment_score = Column(Float)
    negative_count = Column(Integer)
    positive_count = Column(Integer)
    total_count = Column(Integer)
    trend_direction = Column(String)  # up, down, stable
