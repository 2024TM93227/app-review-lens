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


# Actionable PM recommendations per category
CATEGORY_RECOMMENDATIONS: Dict[str, Dict[str, str]] = {
    "delivery_time": {
        "action": "Investigate courier allocation and ETA accuracy",
        "detail": "Audit delivery SLA breaches in the last sprint. Check if peak-hour demand is exceeding rider supply. Review ETA prediction model drift.",
        "owner": "Logistics / Operations",
    },
    "delivery_agent": {
        "action": "Review rider conduct and training program",
        "detail": "Flag top-offending riders for retraining. Audit food tamper-proofing (sealed bags). Add post-delivery rating nudge for rider feedback.",
        "owner": "Operations / Trust & Safety",
    },
    "food_quality": {
        "action": "Tighten restaurant quality SLAs and packaging standards",
        "detail": "Identify restaurants with repeat quality complaints. Enforce hot-bag usage. Consider adding quality score to restaurant ranking algorithm.",
        "owner": "Restaurant Partnerships",
    },
    "order_accuracy": {
        "action": "Improve order verification at restaurant handoff",
        "detail": "Add item-level confirmation checklist for restaurant partners. Investigate if menu sync issues are causing substitutions.",
        "owner": "Product / Restaurant Ops",
    },
    "packaging": {
        "action": "Mandate spill-proof packaging for liquid items",
        "detail": "Audit packaging SLA compliance. Require sealed containers for soups, beverages, and curries. Add packaging quality as a restaurant metric.",
        "owner": "Restaurant Partnerships / Supply",
    },
    "app_experience": {
        "action": "Prioritize crash fixes and performance optimization",
        "detail": "Check crash analytics (Firebase/Sentry) for top crash signatures. Profile app startup time and API latency on low-end devices.",
        "owner": "Engineering / Mobile",
    },
    "payment": {
        "action": "Fix payment failure retry flow and expedite refunds",
        "detail": "Audit payment gateway failure rates by provider. Reduce refund SLA from 7 days to 48 hours. Add auto-retry for transient failures.",
        "owner": "Payments / FinOps",
    },
    "pricing": {
        "action": "Improve pricing transparency and fee breakdown",
        "detail": "Show itemized fee breakdown before checkout (delivery fee, platform fee, taxes). Evaluate if surge pricing thresholds need adjustment.",
        "owner": "Product / Pricing",
    },
    "promotions_offers": {
        "action": "Fix promo code application flow and clarify offer terms",
        "detail": "Audit coupon validation logic for edge cases. Add clear eligibility criteria on offer cards. Track coupon failure reasons.",
        "owner": "Growth / Marketing",
    },
    "customer_support": {
        "action": "Reduce support response time and improve resolution rate",
        "detail": "Audit first-response SLA. Reduce bot-only interactions for high-severity issues. Add escalation path visibility in the app.",
        "owner": "Customer Support / CX",
    },
    "restaurant_issue": {
        "action": "Improve restaurant availability and prep-time accuracy",
        "detail": "Audit restaurant cancellation rates. Enforce real-time menu availability updates. Penalize repeated last-minute closures.",
        "owner": "Restaurant Partnerships",
    },
}


def get_recommendation(category: str) -> Dict[str, str]:
    """Return the actionable recommendation for a given issue category."""
    return CATEGORY_RECOMMENDATIONS.get(category, {
        "action": "Investigate user complaints in this area",
        "detail": "Review sample reviews to identify root cause patterns.",
        "owner": "Product",
    })


def generate_smart_recommendation(category: str, reviews: List[Dict]) -> Dict[str, str]:
    """
    Generate a data-driven recommendation by analyzing actual review content.

    Extracts the most frequently mentioned pain-point keywords from the reviews,
    then enriches the static recommendation with evidence from the data.
    """
    base = get_recommendation(category)

    if not reviews:
        return base

    # Count which category keywords actually appear in these reviews
    keywords = CATEGORY_KEYWORDS.get(category, [])
    keyword_hits: Dict[str, int] = {}
    for r in reviews:
        text_lower = (r.get("text") or "").lower()
        for kw in keywords:
            if kw in text_lower:
                keyword_hits[kw] = keyword_hits.get(kw, 0) + 1

    # Top 5 user-mentioned pain points
    top_phrases = sorted(keyword_hits.items(), key=lambda x: x[1], reverse=True)[:5]

    if not top_phrases:
        return base

    total = len(reviews)
    neg_count = sum(1 for r in reviews if r.get("sentiment") == "negative")
    avg_rating = sum(r.get("rating", 3) for r in reviews) / total

    # Build evidence string from actual data
    phrase_summary = ", ".join(
        f'"{kw}" ({count} mentions)' for kw, count in top_phrases
    )

    evidence_detail = (
        f"Based on {total} user reviews (avg rating {avg_rating:.1f}★, "
        f"{neg_count} negative): users most frequently mention {phrase_summary}. "
        f"{base['detail']}"
    )

    return {
        "action": base["action"],
        "detail": evidence_detail,
        "owner": base["owner"],
        "top_complaints": [kw for kw, _ in top_phrases],
        "evidence_count": total,
    }


def get_all_categories() -> List[str]:
    """Return list of all supported category names."""
    return list(CATEGORY_KEYWORDS.keys())
