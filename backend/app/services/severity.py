"""
V2 Severity Scoring Module
Combines rating, sentiment score, and strong negative keywords into a severity score.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

# Strong negative keywords that elevate severity
STRONG_NEGATIVE_KEYWORDS = [
    "worst", "never", "always", "terrible", "horrible", "disgusting",
    "scam", "fraud", "cheat", "dangerous", "unacceptable", "pathetic",
    "useless", "hate", "disaster", "nightmare", "awful", "rubbish",
    "trash", "zero", "impossible", "furious", "outrageous",
]


def calculate_severity(
    rating: int,
    sentiment_score: float,
    text: str,
    max_score: float = 10.0,
) -> float:
    """
    Calculate a severity score (0–10) for a single review.

    Factors & weights:
      - Rating component (40%): lower rating → higher severity
      - Sentiment component (35%): lower sentiment → higher severity
      - Keyword intensity (25%): presence of strong negatives

    Args:
        rating: 1-5 star rating
        sentiment_score: 0-1 (0=most negative, 1=most positive)
        text: raw review text
        max_score: maximum severity (default 10)

    Returns:
        severity score between 0 and max_score
    """
    # Rating component: 1-star → 1.0, 5-star → 0.0
    rating_component = max(0.0, (5 - rating) / 4.0)

    # Sentiment component: 0.0 sentiment → 1.0, 1.0 sentiment → 0.0
    sentiment_component = max(0.0, 1.0 - sentiment_score)

    # Keyword intensity: count of strong negative keywords (capped at 5)
    text_lower = text.lower() if text else ""
    keyword_hits = sum(1 for kw in STRONG_NEGATIVE_KEYWORDS if kw in text_lower)
    keyword_component = min(keyword_hits / 5.0, 1.0)

    # Weighted combination
    severity = (
        0.40 * rating_component
        + 0.35 * sentiment_component
        + 0.25 * keyword_component
    )

    return round(severity * max_score, 2)


def calculate_severity_batch(reviews: List[dict]) -> List[dict]:
    """
    Calculate severity for a batch of reviews.
    Each review dict must have: rating, sentiment_score, text.
    Returns the same list with 'severity' field added.
    """
    for review in reviews:
        review["severity"] = calculate_severity(
            rating=review.get("rating", 3),
            sentiment_score=review.get("sentiment_score", 0.5),
            text=review.get("text", ""),
        )
    return reviews
