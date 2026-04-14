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

    # Boost negative words common in app/food-delivery reviews that VADER underweights
    _review_lexicon_updates = {
        # Delivery issues
        "late": -2.0,
        "delayed": -2.0,
        "delay": -1.8,
        "waiting": -1.2,
        "wait": -1.0,
        "slow": -1.8,
        "cold": -1.5,
        "stale": -2.0,
        "soggy": -1.5,
        "undercooked": -2.0,
        "raw": -1.2,
        "spilled": -1.8,
        "leaked": -1.5,
        # Order accuracy
        "wrong": -2.0,
        "missing": -2.0,
        "incorrect": -2.0,
        "incomplete": -1.8,
        # App issues
        "crash": -2.5,
        "crashes": -2.5,
        "bug": -2.0,
        "bugs": -2.0,
        "freeze": -2.0,
        "freezes": -2.0,
        "glitch": -2.0,
        "glitchy": -2.0,
        "laggy": -1.8,
        "lag": -1.5,
        "hangs": -1.8,
        "unresponsive": -2.0,
        "error": -1.5,
        "broken": -2.0,
        # Payment / refund
        "overcharged": -2.5,
        "refund": -1.5,
        "charged": -1.0,
        "scam": -3.0,
        "fraud": -3.0,
        "cheat": -2.5,
        "steal": -2.5,
        "stealing": -2.5,
        # Support issues
        "rude": -2.0,
        "unhelpful": -2.0,
        "ignored": -1.8,
        "unresponsive": -2.0,
        "no response": -2.0,
        # General negative
        "disappointed": -2.0,
        "disappointing": -2.0,
        "frustrating": -2.0,
        "frustrated": -2.0,
        "annoying": -1.8,
        "annoyed": -1.5,
        "garbage": -2.5,
        "trash": -2.5,
        "rubbish": -2.5,
        "pathetic": -2.5,
        "ridiculous": -2.0,
        "unacceptable": -2.5,
        "unusable": -2.5,
        "useless": -2.5,
        "waste": -2.0,
        "regret": -2.0,
        "worst": -3.0,
        "horrible": -3.0,
        "terrible": -3.0,
        "disgusting": -3.0,
        "awful": -3.0,
        "nightmare": -2.5,
        "disaster": -2.5,
        "never again": -3.0,
        "uninstall": -2.5,
        "uninstalled": -2.5,
        "deleted": -1.5,
        "not working": -2.0,
        "doesn't work": -2.0,
        "don't use": -2.0,
        "stay away": -2.5,
        "avoid": -2.0,
    }
    for word, score in _review_lexicon_updates.items():
        _vader.lexicon[word] = score

    VADER_AVAILABLE = True
    logger.info("VADER sentiment analyzer loaded with review lexicon updates")
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

    if compound >= 0.15:
        label = "positive"
    elif compound <= -0.10:
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
        "disappointed", "disappointing", "frustrating", "annoying", "useless",
        "waste", "garbage", "trash", "rubbish", "pathetic", "ridiculous",
        "unacceptable", "broken", "error", "bug", "freeze", "glitch",
        "delayed", "cold", "stale", "missing", "overcharged", "scam",
        "fraud", "rude", "unhelpful", "ignored", "uninstall", "avoid",
        "regret", "nightmare", "disaster", "unusable", "laggy",
    ]
    neutral_tokens = [
        "okay", "ok", "average", "decent", "fine", "alright", "mediocre",
        "nothing special", "so-so", "mixed", "moderate", "fair",
    ]

    pos = sum(text_lower.count(w) for w in positive_tokens)
    neg = sum(text_lower.count(w) for w in negative_tokens)
    neu = sum(text_lower.count(w) for w in neutral_tokens)

    if neu > pos and neu > neg:
        return "neutral", 0.5
    if pos > neg:
        score = min(0.9, 0.5 + 0.1 * (pos - neg))
        return "positive", score
    if neg > pos:
        score = max(0.1, 0.5 - 0.1 * (neg - pos))
        return "negative", score
    return "neutral", 0.5


def analyze_sentiment_v2(text: str, rating: int = None) -> Tuple[str, float]:
    """
    Main entry point for V2 sentiment analysis.
    Uses VADER if available, otherwise keyword heuristics.
    When a star rating is provided, it corrects misclassifications:
      - rating <= 2: force negative if text says positive/neutral
      - rating == 3: force neutral if text says positive
      - rating >= 4: keep text-based label as-is
    """
    if not text or not text.strip():
        return "neutral", 0.5

    if VADER_AVAILABLE:
        label, score = analyze_sentiment_vader(text)
    else:
        label, score = analyze_sentiment_keywords(text)

    # Correct sentiment when rating clearly contradicts text analysis
    if rating is not None:
        if rating <= 2 and label != "negative":
            label = "negative"
            score = min(score, 0.35)
        elif rating == 3 and label == "positive":
            label = "neutral"
            score = min(score, 0.50)
        elif rating >= 4 and label == "negative":
            label = "neutral"
            score = max(score, 0.45)

    return label, score
