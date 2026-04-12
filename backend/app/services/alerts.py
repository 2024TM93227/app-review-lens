"""
V2 Alerts System
Detects spikes by comparing last 7 days vs previous 7 days.
Generates alerts when negative sentiment increase > 30%.
"""
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict

logger = logging.getLogger(__name__)


def detect_alerts(
    reviews: List[dict],
    spike_threshold: float = 0.30,
    window_days: int = 7,
) -> List[Dict]:
    """
    Compare last `window_days` vs previous `window_days`.
    If negative-sentiment review count increases by more than `spike_threshold` (30%),
    generate an alert.

    Args:
        reviews: list of review dicts with 'timestamp', 'sentiment', 'sentiment_score',
                 'domain_category' (or 'issue_category')
        spike_threshold: fractional increase to trigger alert (0.30 = 30%)
        window_days: comparison window size

    Returns:
        List of alert dicts
    """
    now = datetime.now()
    recent_start = now - timedelta(days=window_days)
    previous_start = now - timedelta(days=window_days * 2)

    recent_reviews = []
    previous_reviews = []

    for r in reviews:
        ts = r.get("timestamp")
        if not ts:
            continue
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts >= recent_start:
            recent_reviews.append(r)
        elif ts >= previous_start:
            previous_reviews.append(r)

    alerts = []

    # Overall negative sentiment spike
    recent_neg = sum(1 for r in recent_reviews if r.get("sentiment") == "negative")
    prev_neg = sum(1 for r in previous_reviews if r.get("sentiment") == "negative")

    if prev_neg > 0:
        change_pct = (recent_neg - prev_neg) / prev_neg
        if change_pct > spike_threshold:
            alerts.append({
                "type": "negative_sentiment_spike",
                "severity": "critical" if change_pct > 0.5 else "high",
                "message": f"Negative reviews increased {int(change_pct * 100)}% this week ({prev_neg} → {recent_neg})",
                "previous_count": prev_neg,
                "current_count": recent_neg,
                "change_percentage": round(change_pct * 100, 1),
                "detected_at": now.isoformat(),
            })
    elif recent_neg > 3:
        # New surge from zero baseline
        alerts.append({
            "type": "negative_sentiment_spike",
            "severity": "high",
            "message": f"New wave of {recent_neg} negative reviews detected this week (none previously)",
            "previous_count": 0,
            "current_count": recent_neg,
            "change_percentage": 100.0,
            "detected_at": now.isoformat(),
        })

    # Per-category spikes
    category_alerts = _detect_category_spikes(
        recent_reviews, previous_reviews, spike_threshold, now
    )
    alerts.extend(category_alerts)

    return alerts


def _detect_category_spikes(
    recent: List[dict],
    previous: List[dict],
    threshold: float,
    now: datetime,
) -> List[Dict]:
    """Detect per-category spikes."""
    def count_by_category(reviews):
        counts = defaultdict(int)
        for r in reviews:
            cat = r.get("issue_category") or r.get("domain_category") or "unknown"
            if r.get("sentiment") == "negative":
                counts[cat] += 1
        return counts

    recent_counts = count_by_category(recent)
    prev_counts = count_by_category(previous)

    alerts = []
    all_cats = set(list(recent_counts.keys()) + list(prev_counts.keys()))

    for cat in all_cats:
        rc = recent_counts.get(cat, 0)
        pc = prev_counts.get(cat, 0)

        if pc > 0:
            change = (rc - pc) / pc
            if change > threshold:
                label = cat.replace("_", " ").title()
                alerts.append({
                    "type": "category_spike",
                    "category": cat,
                    "severity": "critical" if change > 0.5 else "high",
                    "message": f"{label} complaints increased {int(change * 100)}% this week ({pc} → {rc})",
                    "previous_count": pc,
                    "current_count": rc,
                    "change_percentage": round(change * 100, 1),
                    "detected_at": now.isoformat(),
                })
        elif rc >= 3:
            label = cat.replace("_", " ").title()
            alerts.append({
                "type": "category_spike",
                "category": cat,
                "severity": "medium",
                "message": f"New {label} complaints emerging ({rc} this week)",
                "previous_count": 0,
                "current_count": rc,
                "change_percentage": 100.0,
                "detected_at": now.isoformat(),
            })

    return sorted(alerts, key=lambda a: a.get("change_percentage", 0), reverse=True)
