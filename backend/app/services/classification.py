"""
V2 Issue Classification Module (Food Delivery Ontology)
Keyword-based classification with modular design for future ML upgrade.
"""
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

# Food Delivery Ontology: category → keywords
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "delivery_time": [
        "late", "delay", "delayed", "slow delivery", "took too long",
        "waiting", "wait", "hours", "hour", "delivery time", "not delivered",
        "delivery delayed", "late delivery", "took forever", "still waiting",
        "eta", "estimated time", "delivery slow", "never arrived", "long wait",
    ],
    "food_quality": [
        "cold food", "stale", "raw", "undercooked", "overcooked", "tasteless",
        "bad taste", "spoiled", "rotten", "quality", "food quality",
        "not fresh", "soggy", "dry", "bland", "disgusting", "horrible food",
        "terrible food", "hair in food", "unhygienic", "dirty",
    ],
    "order_accuracy": [
        "wrong item", "wrong order", "missing item", "incorrect order",
        "not what i ordered", "wrong food", "missing", "incomplete order",
        "substitution", "extra item", "quantity wrong", "different item",
        "order mix up", "mixed up", "order accuracy",
    ],
    "app_experience": [
        "crash", "crashes", "bug", "buggy", "freeze", "frozen", "slow app",
        "app not working", "glitch", "error", "lag", "lagging", "loading",
        "ui", "interface", "design", "navigation", "notification",
        "update", "version", "uninstall", "force close", "app stopped",
    ],
    "payment": [
        "payment", "refund", "charged", "double charged", "payment failed",
        "transaction", "money", "wallet", "upi", "card", "debit", "credit",
        "overcharged", "not refunded", "refund pending", "refund not received",
        "payment issue", "billing", "promo code", "coupon", "discount",
    ],
    "customer_support": [
        "support", "customer service", "customer care", "helpline", "help",
        "no response", "complaint", "grievance", "escalation", "chat support",
        "call center", "unhelpful", "rude support", "useless support",
        "bot response", "automated response", "no resolution",
    ],
}

# Mapping from V1 domain categories to V2 categories for backward compatibility
V1_TO_V2_CATEGORY_MAP = {
    "Delivery": "delivery_time",
    "Order": "order_accuracy",
    "Payments": "payment",
    "App": "app_experience",
    "Support": "customer_support",
}


def classify_issue(text: str) -> str:
    """
    Classify a review into one of the food delivery ontology categories.

    Args:
        text: preprocessed review text (lowercase)

    Returns:
        category name string, or "uncategorized" if no match
    """
    if not text:
        return "uncategorized"

    text_lower = text.lower()

    scores: Dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        return "uncategorized"

    return max(scores, key=scores.get)


def classify_issue_multi(text: str) -> List[Tuple[str, int]]:
    """
    Return all matching categories with their match scores, sorted descending.
    Useful for reviews that span multiple categories.
    """
    if not text:
        return []

    text_lower = text.lower()
    results = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            results.append((category, score))

    return sorted(results, key=lambda x: x[1], reverse=True)


def map_v1_category(v1_category: str) -> str:
    """Map a V1 domain_category to a V2 issue classification category."""
    return V1_TO_V2_CATEGORY_MAP.get(v1_category, "uncategorized")


def get_all_categories() -> List[str]:
    """Return list of all supported category names."""
    return list(CATEGORY_KEYWORDS.keys())
