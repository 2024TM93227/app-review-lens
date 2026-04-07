"""
NLP Processing Module: Sentiment, Aspect, and Topic Extraction
"""
from typing import Dict, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Analyze sentiment of review text using simple keyword heuristics
    Returns: (label: positive/negative/neutral, score: 0-1)
    """
    text_lower = text.lower()
    positive_tokens = ['good', 'great', 'love', 'excellent', 'easy', 'fast', 'nice', 'amazing', 'perfect', 'best']
    negative_tokens = ['bad', 'terrible', 'worst', 'slow', 'late', 'poor', 'issue', 'problem', 'hate', 'wrong', 'crash']

    positive_score = sum(text_lower.count(word) for word in positive_tokens)
    negative_score = sum(text_lower.count(word) for word in negative_tokens)

    if positive_score > negative_score:
        score = min(0.9, 0.5 + 0.1 * (positive_score - negative_score))
        return 'positive', score
    if negative_score > positive_score:
        score = max(0.1, 0.5 - 0.1 * (negative_score - positive_score))
        return 'negative', score
    return 'neutral', 0.5


def extract_aspects(text: str) -> Dict[str, str]:
    """
    Extract food-delivery specific aspects from review text
    Returns: {"delivery_time": "negative", "order_accuracy": "positive", ...}
    """
    aspects = {}
    text_lower = text.lower()
    
    # Define aspect keywords and their sentiment indicators
    aspect_keywords = {
        'delivery_time': {
            'keywords': ['delivery', 'late', 'delay', 'fast', 'quick', 'hour', 'minute', 'wait', 'slow'],
            'positive': ['fast', 'quick', 'timely', 'on time', 'delivered', 'arrived'],
            'negative': ['late', 'delay', 'slow', 'took', 'waiting', 'hours']
        },
        'order_accuracy': {
            'keywords': ['wrong', 'missing', 'correct', 'accurate', 'order', 'item', 'quantity', 'substitution'],
            'positive': ['correct', 'accurate', 'right', 'exactly', 'perfect'],
            'negative': ['wrong', 'missing', 'incomplete', 'incorrect', 'different', 'substitution']
        },
        'tracking': {
            'keywords': ['tracking', 'location', 'live', 'map', 'real-time', 'gps', 'locate'],
            'positive': ['accurate', 'real-time', 'works', 'good', 'reliable'],
            'negative': ['not working', 'broken', 'inaccurate', 'stuck', 'lag']
        },
        'ui_ux': {
            'keywords': ['app', 'ui', 'interface', 'button', 'design', 'feature', 'crash', 'freeze', 'slow', 'hang'],
            'positive': ['smooth', 'easy', 'intuitive', 'fast', 'beautiful', 'responsive'],
            'negative': ['crash', 'freeze', 'lag', 'slow', 'confusing', 'buggy', 'broken']
        },
        'payment': {
            'keywords': ['payment', 'refund', 'upi', 'card', 'wallet', 'gateway', 'transaction', 'money'],
            'positive': ['smooth', 'easy', 'accepted', 'refunded', 'quick'],
            'negative': ['failed', 'rejected', 'charged', 'lost', 'refund not received', 'issue']
        },
        'customer_support': {
            'keywords': ['support', 'customer service', 'help', 'contact', 'complaint', 'response', 'helpline'],
            'positive': ['helpful', 'responsive', 'solved', 'resolved', 'quick'],
            'negative': ['no response', 'useless', 'rude', 'unhelpful', 'slow']
        },
        'offers': {
            'keywords': ['offer', 'discount', 'promo', 'coupon', 'deal', 'subscription', 'membership', 'price'],
            'positive': ['good', 'great', 'amazing', 'helpful', 'valuable'],
            'negative': ['not working', 'expired', 'false', 'misleading', 'poor']
        }
    }
    
    # Extract aspects
    for aspect, keywords_dict in aspect_keywords.items():
        if any(kw in text_lower for kw in keywords_dict['keywords']):
            # Simple sentiment scoring for aspect
            positive_count = sum(1 for kw in keywords_dict['positive'] if kw in text_lower)
            negative_count = sum(1 for kw in keywords_dict['negative'] if kw in text_lower)
            
            if negative_count > positive_count:
                aspects[aspect] = 'negative'
            elif positive_count > negative_count:
                aspects[aspect] = 'positive'
            else:
                aspects[aspect] = 'neutral'
    
    return aspects


def classify_domain_category(text: str) -> Tuple[str, str]:
    """
    Classify review into food-delivery domain categories
    Returns: (category, subcategory)
    """
    text_lower = text.lower()
    
    # Domain ontology for food-delivery
    domain_rules = {
        'Delivery': {
            'Delay': ['late delivery', 'delivery delayed', 'took too long', 'delayed delivery', 'waiting hours'],
            'Courier_Behavior': ['rude delivery', 'unprofessional', 'courier behavior', 'delivery person', 'driver rude'],
            'Packaging': ['broken', 'damaged', 'wet food', 'spilled', 'wrong packaging', 'poor packaging']
        },
        'Order': {
            'Accuracy': ['wrong item', 'missing item', 'incorrect order', 'not what i ordered', 'wrong food'],
            'Substitution': ['substitution', 'item substituted', 'replacement', 'alternative item'],
            'Cancellation': ['order cancelled', 'cancelled without reason', 'cancelled automatically', 'sudden cancellation']
        },
        'Payments': {
            'Transaction': ['payment failed', 'transaction failed', 'payment issue', 'payment declined'],
            'Refund': ['refund not received', 'refund pending', 'money not refunded', 'refund issue', 'pending refund'],
            'Methods': ['upi issue', 'card issue', 'wallet issue', 'payment method', 'cash on delivery']
        },
        'App': {
            'Crashes': ['app crash', 'keeps crashing', 'crashes', 'force close', 'app stopped'],
            'Performance': ['slow', 'lag', 'loading time', 'freeze', 'hang', 'not responding'],
            'Notifications': ['notification issue', 'not getting notification', 'notification spam', 'notification error']
        },
        'Support': {
            'Response': ['no response from support', 'slow response', 'complaint not addressed', 'customer support', 'customer service'],
            'Resolution': ['complaint not resolved', 'issue not resolved', 'support useless'],
            'Accessibility': ['cant contact support', 'no help available', 'helpline unreachable']
        }
    }
    
    # Find best matching domain
    for category, subcategories in domain_rules.items():
        for subcategory, keywords in subcategories.items():
            if any(kw in text_lower for kw in keywords):
                return category, subcategory
    
    return 'General', 'Other'


def extract_entities_and_numbers(text: str) -> Dict[str, any]:
    """Extract important entities and numbers from review text"""
    entities = {}
    
    # Extract timestamps
    if 'hour' in text.lower() or 'minute' in text.lower():
        hours = re.findall(r'(\d+)\s*hour', text.lower())
        minutes = re.findall(r'(\d+)\s*minute', text.lower())
        if hours:
            entities['hours_mentioned'] = int(hours[0])
        if minutes:
            entities['minutes_mentioned'] = int(minutes[0])
    
    # Extract ratings/scores
    ratings = re.findall(r'\b([0-5])\s*(?:out of\s*5|star)', text)
    if ratings:
        entities['embedded_rating'] = int(ratings[0])
    
    # Check for money mentions
    amounts = re.findall(r'[₹$€]\s*(\d+)', text)
    if amounts:
        entities['amounts_mentioned'] = [int(a) for a in amounts]
    
    return entities


def preprocess_text(text: str) -> str:
    """
    Clean and normalize review text
    """
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Keep alphanumeric, spaces, and basic punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.!?,;:\'-]', '', text)
    
    return text.strip()


def detect_spam(text: str) -> bool:
    """Detect likely spam/bot reviews"""
    text_lower = text.lower()
    
    # Boilerplate patterns
    spam_patterns = [
        r'buy.*viagra',
        r'casino',
        r'lottery',
        r'click\s*here',
        r'visit.*now',
        r'limited\s*time\s*offer',
        r'act\s*now',
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Check for all caps (likely spam)
    if len(text) > 20 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
        return True
    
    # Check for excessive punctuation
    punct_count = sum(1 for c in text if c in '!?.')
    if punct_count / len(text) > 0.3:
        return True
    
    return False
