"""
Prioritization Engine: Score and rank issues by impact
"""
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_priority_score(
    frequency: int,
    sentiment_score: float,
    rating: int = 3,
    days_old: int = 0,
    max_days: int = 30
) -> float:
    """
    Calculate composite priority score for an issue
    
    Factors:
    - Frequency: How many reviews mention this issue (weight: 0.4)
    - Sentiment: How negative is the sentiment (weight: 0.3)
    - Rating: Lower ratings = higher priority (weight: 0.2)
    - Recency: Recent issues ranked higher (weight: 0.1)
    
    Returns: 0-100 priority score
    """
    # Frequency score (0-1, normalized)
    frequency_score = min(frequency / 50, 1.0)  # 50+ issues = max score
    
    # Sentiment score (0-1, already normalized)
    # For negative sentiment, use as-is; for positive, invert
    if sentiment_score < 0.5:
        sentiment_component = (0.5 - sentiment_score) * 2  # 0-1
    else:
        sentiment_component = 0
    
    # Rating score (0-1)
    rating_score = max(0, (5 - rating) / 5)  # 1-star = 1.0, 5-star = 0
    
    # Recency score (0-1)
    recency_score = max(0, 1 - (days_old / max_days))
    
    # Weighted composite
    priority = (
        0.40 * frequency_score +
        0.30 * sentiment_component +
        0.20 * rating_score +
        0.10 * recency_score
    )
    
    return min(100, priority * 100)  # Scale to 0-100


def rank_issues(issues: List[Dict]) -> List[Dict]:
    """
    Rank issues by priority score
    Returns sorted list with rank field added
    """
    # Sort by priority_score descending
    sorted_issues = sorted(issues, key=lambda x: x.get('priority_score', 0), reverse=True)
    
    # Add rank
    for idx, issue in enumerate(sorted_issues, 1):
        issue['rank'] = idx
    
    return sorted_issues


def calculate_issue_metrics(reviews_data: List[Dict], issue_keywords: List[str]) -> Dict:
    """
    Calculate metrics for an issue category
    
    Input: List of review dicts and keywords to search for
    Output: Metrics dict with frequency, sentiment, rating, etc.
    """
    matching_reviews = [
        r for r in reviews_data 
        if any(kw.lower() in r.get('content', '').lower() for kw in issue_keywords)
    ]
    
    if not matching_reviews:
        return None
    
    sentiment_scores = [r.get('sentiment_score', 0.5) for r in matching_reviews]
    ratings = [r.get('rating', 3) for r in matching_reviews]
    
    # Calculate days since first mention
    timestamps = [r.get('timestamp') for r in matching_reviews if r.get('timestamp')]
    if timestamps:
        oldest = min(timestamps)
        days_old = (datetime.now() - oldest).days
    else:
        days_old = 0
    
    metrics = {
        'frequency': len(matching_reviews),
        'avg_sentiment_score': sum(sentiment_scores) / len(sentiment_scores),
        'avg_rating': sum(ratings) / len(ratings),
        'days_since_first_mention': days_old,
        'sample_reviews': [r.get('review_id') for r in matching_reviews[:5]],
    }
    
    # Calculate priority
    metrics['priority_score'] = calculate_priority_score(
        frequency=metrics['frequency'],
        sentiment_score=metrics['avg_sentiment_score'],
        rating=metrics['avg_rating'],
        days_old=days_old
    )
    
    return metrics


def detect_sentiment_spikes(
    trend_data: List[Dict],
    baseline_window: int = 7,
    alert_threshold: float = 0.15
) -> List[Dict]:
    """
    Detect unusual spikes in negative sentiment
    """
    alerts = []
    
    for i in range(baseline_window, len(trend_data)):
        # Calculate baseline (previous week)
        baseline_period = trend_data[i-baseline_window:i]
        baseline_avg = sum(t.get('avg_sentiment_score', 0.5) for t in baseline_period) / baseline_window
        
        # Current value
        current = trend_data[i]
        current_sentiment = current.get('avg_sentiment_score', 0.5)
        
        # Detect spike (sudden drop in sentiment = increase in negativity)
        sentiment_change = baseline_avg - current_sentiment
        if sentiment_change > alert_threshold:
            alerts.append({
                'date': current.get('date'),
                'aspect': current.get('aspect'),
                'baseline_sentiment': baseline_avg,
                'current_sentiment': current_sentiment,
                'change': sentiment_change,
                'severity': 'critical' if sentiment_change > 0.25 else 'high'
            })
    
    return alerts


def calculate_release_impact(reviews_before: List[Dict], reviews_after: List[Dict]) -> Dict:
    """
    Calculate sentiment and issue impact of app release
    """
    def aggregate_metrics(reviews):
        if not reviews:
            return {}
        
        sentiments = [r.get('sentiment_score', 0.5) for r in reviews]
        ratings = [r.get('rating', 3) for r in reviews]
        
        return {
            'avg_sentiment': sum(sentiments) / len(sentiments),
            'avg_rating': sum(ratings) / len(ratings),
            'volume': len(reviews),
            'sentiment_std': calculate_std(sentiments) if sentiments else 0,
        }
    
    before_metrics = aggregate_metrics(reviews_before)
    after_metrics = aggregate_metrics(reviews_after)
    
    impact = {
        'sentiment_change': after_metrics.get('avg_sentiment', 0.5) - before_metrics.get('avg_sentiment', 0.5),
        'rating_change': after_metrics.get('avg_rating', 3) - before_metrics.get('avg_rating', 3),
        'volume_change': after_metrics.get('volume', 0) - before_metrics.get('volume', 0),
        'before': before_metrics,
        'after': after_metrics,
    }
    
    # Determine if release was positive/negative
    if impact['sentiment_change'] > 0.05:
        impact['status'] = 'positive'
    elif impact['sentiment_change'] < -0.05:
        impact['status'] = 'negative'
    else:
        impact['status'] = 'neutral'
    
    return impact


def calculate_std(values: List[float]) -> float:
    """Calculate standard deviation"""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5
