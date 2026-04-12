"""
V2 Sentiment Analysis Module
Uses VADER (vaderSentiment) for robust sentiment scoring.
Falls back to keyword heuristics if VADER is unavailable.
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
    logger.info("VADER sentiment analyzer loaded")
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("vaderSentiment not installed, using keyword fallback")


def analyze_sentiment_vader(text: str) -> Tuple[str, float]:
    """
    Analyze sentiment using VADER.
    Returns: (label, compound_score)
      - label: 'positive', 'negative', or 'neutral'
      - compound_score: -1.0 to 1.0 raw compound, normalized to 0-1 for storage
    """
    scores = _vader.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    # Normalize compound from [-1, 1] to [0, 1] for compatibility with V1 schema
    normalized = (compound + 1) / 2.0
    return label, round(normalized, 4)


def analyze_sentiment_keywords(text: str) -> Tuple[str, float]:
    """Keyword-based fallback (V1 logic preserved)."""
    text_lower = text.lower()
    positive_tokens = [
        "good", "great", "love", "excellent", "easy", "fast", "nice",
        "amazing", "perfect", "best", "awesome", "wonderful", "fantastic",
    ]
    negative_tokens = [
        "bad", "terrible", "worst", "slow", "late", "poor", "issue",
        "problem", "hate", "wrong", "crash", "horrible", "awful", "disgusting",
    ]

    pos = sum(text_lower.count(w) for w in positive_tokens)
    neg = sum(text_lower.count(w) for w in negative_tokens)

    if pos > neg:
        score = min(0.9, 0.5 + 0.1 * (pos - neg))
        return "positive", score
    if neg > pos:
        score = max(0.1, 0.5 - 0.1 * (neg - pos))
        return "negative", score
    return "neutral", 0.5


def analyze_sentiment_v2(text: str) -> Tuple[str, float]:
    """
    Main entry point for V2 sentiment analysis.
    Uses VADER if available, otherwise keyword heuristics.
    """
    if not text or not text.strip():
        return "neutral", 0.5

    if VADER_AVAILABLE:
        return analyze_sentiment_vader(text)
    return analyze_sentiment_keywords(text)
