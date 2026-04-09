"""
Pydantic models for API request/response schema generation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class AspectEnum(str, Enum):
    DELIVERY = "delivery"
    PAYMENT = "payment"
    ORDER = "order"
    APP_UX = "app/ux"
    SUPPORT = "support"


class ReviewResponse(BaseModel):
    id: int
    app_id: str
    review_id: str
    rating: int
    text: str
    sentiment: SentimentEnum
    sentiment_score: float
    timestamp: datetime
    language: str
    country: str

    class Config:
        from_attributes = True


class AspectSentimentResponse(BaseModel):
    aspect: str
    sentiment: SentimentEnum
    confidence: float

    class Config:
        from_attributes = True


class InsightResponse(BaseModel):
    id: int
    app_id: str
    category: str
    subcategory: str
    issue_description: str
    frequency: int
    priority_score: float
    rank: int
    sentiment_score: float
    status: str
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class IngestReviewsRequest(BaseModel):
    app_ids: List[str] = Field(..., description="List of app package IDs to ingest reviews for")
    countries: List[str] = Field(default=["IN"], description="ISO country codes")
    languages: List[str] = Field(default=["en"], description="Language codes")
    since: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    until: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    max_reviews: int = Field(default=1000, description="Max reviews per app")


class IngestReviewsResponse(BaseModel):
    job_id: str
    status: str = "queued"
    app_ids: List[str]
    created_at: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    progress: float  # 0.0 to 100.0
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class IssueMetric(BaseModel):
    issue_id: int
    category: str
    severity: str  # critical, high, medium, low
    frequency: int
    trend: float  # -1 to 1
    rating_impact: float
    is_top_issue: bool = False


class DashboardResponse(BaseModel):
    job_id: str
    app_id: str
    total_reviews: int
    avg_rating: float
    rating_change: float
    top_issue: Optional[IssueMetric] = None
    issues: List[IssueMetric]
    review_sentiment_distribution: Dict[str, int]  # positive, negative, neutral counts


class ComparisonAspect(BaseModel):
    aspect: str
    app_a_score: float
    app_b_score: float
    app_a_positive_pct: float
    app_b_positive_pct: float
    app_a_negative_pct: float
    app_b_negative_pct: float


class ComparisonResponse(BaseModel):
    app_a_id: str
    app_b_id: str
    app_a_rating: float
    app_b_rating: float
    aspects: List[ComparisonAspect]
    app_a_strengths: List[str]
    app_b_weaknesses: List[str]


class EvidenceReview(BaseModel):
    review_id: str
    rating: int
    text: str
    date: datetime
    locale: str
    aspect_sentiment: Optional[str] = None


class IssueDeepDiveResponse(BaseModel):
    issue_id: int
    category: str
    subcategory: str
    frequency: int
    trend_data: List[Dict[str, Any]]  # for trend chart
    evidence_reviews: List[EvidenceReview]


class DecisionRequest(BaseModel):
    job_id: str
    issue_id: int
    action: str
    priority: str  # critical, high, medium, low


class DecisionResponse(BaseModel):
    decision_id: str
    job_id: str
    issue_id: int
    action: str
    priority: str
    created_at: datetime


class AppSearchResponse(BaseModel):
    app_id: str
    name: str
    category: str
    rating: float
    review_count: int
    icon_url: Optional[str] = None
