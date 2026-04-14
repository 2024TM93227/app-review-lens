from datetime import datetime

from app.services.prioritization import aggregate_issues


def _make_review(issue_category: str, rating: int, sentiment_score: float):
    return {
        "issue_category": issue_category,
        "rating": rating,
        "sentiment_score": sentiment_score,
        "text": f"Review about {issue_category}",
        "timestamp": datetime.now(),
    }


def test_aggregate_issues_ranks_higher_frequency_above_lower_frequency_when_other_signals_equal():
    reviews = []

    # High-frequency issue
    reviews.extend(_make_review("order_accuracy", rating=1, sentiment_score=0.1) for _ in range(12))

    # Lower-frequency issue with same rating/sentiment profile
    reviews.extend(_make_review("packaging", rating=1, sentiment_score=0.1) for _ in range(3))

    issues = aggregate_issues(reviews)
    by_name = {issue["name"]: issue for issue in issues}

    assert by_name["order_accuracy"]["frequency"] == 12
    assert by_name["packaging"]["frequency"] == 3
    assert by_name["order_accuracy"]["impact"] > by_name["packaging"]["impact"]
    assert by_name["order_accuracy"]["rank"] < by_name["packaging"]["rank"]
