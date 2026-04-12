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
    "delivery_agent": [
        "delivery boy", "delivery man", "delivery guy", "delivery person",
        "delivery partner", "rider", "driver", "agent", "rude delivery",
        "rude driver", "rude rider", "misbehave", "unprofessional",
        "ate my food", "tampered", "delivery executive", "biker",
        "called me", "argued", "threatening", "not wearing mask",
    ],
    "food_quality": [
        "cold food", "stale", "raw", "undercooked", "overcooked", "tasteless",
        "bad taste", "spoiled", "rotten", "quality", "food quality",
        "not fresh", "soggy", "dry", "bland", "disgusting", "horrible food",
        "terrible food", "hair in food", "unhygienic", "dirty", "oily",
        "smell", "smelly", "expired", "fungus", "insect", "cockroach",
    ],
    "order_accuracy": [
        "wrong item", "wrong order", "missing item", "incorrect order",
        "not what i ordered", "wrong food", "missing", "incomplete order",
        "substitution", "extra item", "quantity wrong", "different item",
        "order mix up", "mixed up", "order accuracy", "half quantity",
        "less quantity", "wrong restaurant", "swapped",
    ],
    "packaging": [
        "packaging", "packed", "spilled", "leaked", "broken seal",
        "container", "open container", "torn", "messy", "spillage",
        "lid open", "not sealed", "damaged package", "wet bag",
        "loose packing", "poor packing",
    ],
    "app_experience": [
        "crash", "crashes", "bug", "buggy", "freeze", "frozen", "slow app",
        "app not working", "glitch", "error", "lag", "lagging", "loading",
        "ui", "interface", "design", "navigation", "notification",
        "update", "version", "uninstall", "force close", "app stopped",
        "login", "otp", "sign in", "logout", "session", "not opening",
    ],
    "payment": [
        "payment", "refund", "charged", "double charged", "payment failed",
        "transaction", "money", "wallet", "upi", "card", "debit", "credit",
        "overcharged", "not refunded", "refund pending", "refund not received",
        "payment issue", "billing",
    ],
    "pricing": [
        "expensive", "costly", "overpriced", "price", "pricing",
        "delivery fee", "delivery charge", "surge", "surge pricing",
        "packing charge", "platform fee", "hidden charges", "too much",
        "high price", "markup", "price hike", "not worth",
    ],
    "promotions_offers": [
        "promo code", "coupon", "discount", "offer", "cashback",
        "promo not working", "coupon not applied", "no discount",
        "fake offer", "misleading offer", "expired coupon",
        "deal", "reward", "loyalty", "subscription", "pro membership",
    ],
    "customer_support": [
        "support", "customer service", "customer care", "helpline", "help",
        "no response", "complaint", "grievance", "escalation", "chat support",
        "call center", "unhelpful", "rude support", "useless support",
        "bot response", "automated response", "no resolution",
    ],
    "restaurant_issue": [
        "restaurant", "restaurant closed", "not available", "out of stock",
        "menu", "preparation time", "restaurant cancel", "cancelled by restaurant",
        "shop closed", "long preparation", "restaurant not accepting",
        "options not available", "limited menu",
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


def _compute_scores(text_lower: str) -> Dict[str, float]:
    """Score each category by keyword matches, weighting multi-word phrases higher."""
    scores: Dict[str, float] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in text_lower:
                # Multi-word phrases get proportionally higher weight
                score += len(kw.split())
        if score > 0:
            scores[category] = score
    return scores


# Fallback: map very common words that are too generic for the main keyword lists
_FALLBACK_WORDS: Dict[str, str] = {
    "deliver": "delivery_time",
    "order": "order_accuracy",
    "food": "food_quality",
    "taste": "food_quality",
    "pay": "payment",
    "price": "pricing",
    "cost": "pricing",
    "app": "app_experience",
    "support": "customer_support",
    "pack": "packaging",
    "offer": "promotions_offers",
    "restaurant": "restaurant_issue",
    "rider": "delivery_agent",
    "driver": "delivery_agent",
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

    scores = _compute_scores(text_lower)

    if scores:
        return max(scores, key=scores.get)  # type: ignore[arg-type]

    # Fallback: check single-word stems
    for word, category in _FALLBACK_WORDS.items():
        if word in text_lower:
            return category

    return "uncategorized"


def classify_issue_multi(text: str) -> List[Tuple[str, float]]:
    """
    Return all matching categories with their match scores, sorted descending.
    Useful for reviews that span multiple categories.
    """
    if not text:
        return []

    scores = _compute_scores(text.lower())
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def map_v1_category(v1_category: str) -> str:
    """Map a V1 domain_category to a V2 issue classification category."""
    return V1_TO_V2_CATEGORY_MAP.get(v1_category, "uncategorized")


def get_all_categories() -> List[str]:
    """Return list of all supported category names."""
    return list(CATEGORY_KEYWORDS.keys())
