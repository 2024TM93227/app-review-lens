"""
Trend Detection & Anomaly Monitoring Module
Tracks sentiment trends, detects spikes, and identifies emerging issues
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def build_sentiment_trend(reviews: List[Dict], bucket: str = 'daily') -> List[Dict]:
    """
    Build sentiment trend over time
    
    Args:
        reviews: List of review dicts with sentiment_score, timestamp
        bucket: 'daily', 'weekly', or 'hourly'
    
    Returns: List of trend points with date and metrics
    """
    trend_dict = defaultdict(lambda: {
        "positive": 0, 
        "negative": 0, 
        "neutral": 0,
        "total": 0,
        "scores": []
    })
    
    for review in reviews:
        timestamp = review.get('timestamp')
        if not timestamp:
            continue
        
        # Convert to datetime if string
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Bucket by requested granularity
        if bucket == 'hourly':
            date_key = timestamp.strftime('%Y-%m-%d %H:00')
        elif bucket == 'weekly':
            date_key = (timestamp - timedelta(days=timestamp.weekday())).strftime('%Y-%m-%d')
        else:  # daily
            date_key = timestamp.strftime('%Y-%m-%d')
        
        sentiment_score = review.get('sentiment_score', 0.5)
        trend_dict[date_key]['scores'].append(sentiment_score)
        trend_dict[date_key]['total'] += 1
        
        if sentiment_score > 0.6:
            trend_dict[date_key]['positive'] += 1
        elif sentiment_score < 0.4:
            trend_dict[date_key]['negative'] += 1
        else:
            trend_dict[date_key]['neutral'] += 1
    
    # Convert to list and calculate averages
    trend_list = []
    for date_key in sorted(trend_dict.keys()):
        data = trend_dict[date_key]
        avg_sentiment = sum(data['scores']) / len(data['scores']) if data['scores'] else 0.5
        
        trend_list.append({
            'date': date_key,
            'avg_sentiment_score': avg_sentiment,
            'positive_count': data['positive'],
            'negative_count': data['negative'],
            'neutral_count': data['neutral'],
            'total_count': data['total'],
            'positive_percentage': (data['positive'] / data['total'] * 100) if data['total'] > 0 else 0,
            'negative_percentage': (data['negative'] / data['total'] * 100) if data['total'] > 0 else 0,
        })
    
    return trend_list


def build_aspect_trend(reviews: List[Dict], aspect: str, bucket: str = 'daily') -> List[Dict]:
    """
    Build trend for specific aspect (e.g., 'delivery_time', 'order_accuracy')
    """
    aspect_reviews = [
        r for r in reviews 
        if r.get('aspects') and aspect in r.get('aspects', {})
    ]
    
    return build_sentiment_trend(aspect_reviews, bucket)


def detect_change_points(trend_data: List[Dict], sensitivity: float = 1.5) -> List[Dict]:
    """
    Detect significant sentiment changes using change-point detection
    
    Args:
        trend_data: List of daily sentiment trend data
        sensitivity: Threshold multiplier for detecting changes (higher = less sensitive)
    
    Returns: List of detected change points
    """
    if len(trend_data) < 3:
        return []
    
    change_points = []
    
    for i in range(1, len(trend_data) - 1):
        prev_sentiment = trend_data[i-1]['avg_sentiment_score']
        curr_sentiment = trend_data[i]['avg_sentiment_score']
        next_sentiment = trend_data[i+1]['avg_sentiment_score']
        
        # Calculate change magnitude
        change = abs(curr_sentiment - prev_sentiment)
        
        # Simple threshold-based detection
        if change > 0.15 * sensitivity:
            direction = 'improvement' if (curr_sentiment > prev_sentiment) else 'degradation'
            
            change_points.append({
                'date': trend_data[i]['date'],
                'change': change,
                'direction': direction,
                'prev_sentiment': prev_sentiment,
                'curr_sentiment': curr_sentiment,
                'severity': 'critical' if change > 0.3 else 'high' if change > 0.2 else 'medium'
            })
    
    return change_points


def detect_issue_bursts(reviews: List[Dict], keywords_map: Dict[str, List[str]], 
                        threshold_percentile: float = 75) -> List[Dict]:
    """
    Detect sudden spikes in specific issue mentions
    
    Args:
        reviews: List of reviews with content and timestamp
        keywords_map: {"issue_name": ["keyword1", "keyword2"]}
        threshold_percentile: Percentile above which to flag as burst
    
    Returns: List of detected issue bursts
    """
    bursts = []
    
    # Build daily issue mention trends
    for issue_name, keywords in keywords_map.items():
        daily_counts = defaultdict(int)
        
        for review in reviews:
            content = review.get('content', '').lower()
            timestamp = review.get('timestamp')
            
            if not timestamp:
                continue
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            date_key = timestamp.strftime('%Y-%m-%d')
            
            # Count keyword mentions
            if any(kw.lower() in content for kw in keywords):
                daily_counts[date_key] += 1
        
        if not daily_counts:
            continue
        
        # Calculate threshold
        counts_list = list(daily_counts.values())
        threshold = sorted(counts_list)[int(len(counts_list) * threshold_percentile / 100)]
        
        # Detect bursts
        for date_key in sorted(daily_counts.keys()):
            if daily_counts[date_key] > threshold:
                bursts.append({
                    'date': date_key,
                    'issue': issue_name,
                    'mentions': daily_counts[date_key],
                    'threshold': threshold,
                    'spike_percentage': ((daily_counts[date_key] - threshold) / threshold * 100) if threshold > 0 else 0
                })
    
    return bursts


def calculate_rolling_metrics(reviews: List[Dict], window_days: int = 7) -> List[Dict]:
    """
    Calculate rolling window metrics (7-day, 14-day, 30-day averages)
    """
    if not reviews:
        return []
    
    # Group by date
    date_groups = defaultdict(list)
    for review in reviews:
        timestamp = review.get('timestamp')
        if not timestamp:
            continue
        
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        date_key = timestamp.strftime('%Y-%m-%d')
        date_groups[date_key].append(review)
    
    # Calculate rolling average
    sorted_dates = sorted(date_groups.keys())
    rolling_metrics = []
    
    for i, current_date in enumerate(sorted_dates):
        window_start = i - window_days + 1
        if window_start < 0:
            window_start = 0
        
        window_reviews = []
        for j in range(window_start, i + 1):
            window_reviews.extend(date_groups[sorted_dates[j]])
        
        if window_reviews:
            sentiments = [r.get('sentiment_score', 0.5) for r in window_reviews]
            ratings = [r.get('rating', 3) for r in window_reviews]
            
            rolling_metrics.append({
                'date': current_date,
                f'{window_days}_day_avg_sentiment': sum(sentiments) / len(sentiments),
                f'{window_days}_day_avg_rating': sum(ratings) / len(ratings),
                f'{window_days}_day_volume': len(window_reviews),
            })
    
    return rolling_metrics


def identify_emerging_issues(reviews: List[Dict], lookback_days: int = 7) -> List[Dict]:
    """
    Identify new issues that weren't mentioned before
    """
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    recent_reviews = [
        r for r in reviews
        if r.get('timestamp') and datetime.fromisoformat(r['timestamp']) > cutoff_date
    ]
    
    if not recent_reviews:
        return []
    
    # Extract n-grams from recent reviews
    all_bigrams = defaultdict(int)
    
    for review in recent_reviews:
        content = review.get('content', '').lower().split()
        
        for i in range(len(content) - 1):
            bigram = f"{content[i]} {content[i+1]}"
            all_bigrams[bigram] += 1
    
    # Filter for meaningful bigrams (not too common, not too rare)
    emerging = []
    for bigram, count in all_bigrams.items():
        if 2 < count < len(recent_reviews) / 10:
            # Likely an emerging issue
            emerging.append({
                'phrase': bigram,
                'mentions': count,
                'percentage': count / len(recent_reviews) * 100
            })
    
    return sorted(emerging, key=lambda x: x['mentions'], reverse=True)[:10]
