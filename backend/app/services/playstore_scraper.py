"""
PlayStore Review Ingestion Module
Fetches public reviews from Google Play Store for target apps
"""
from google_play_scraper import reviews, Sort, exceptions, app as gplay_app
import logging
from typing import List, Dict
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

# Food-delivery app IDs to monitor
FOOD_DELIVERY_APPS = {
    'Swiggy': 'com.swiggy.swiggy',
    'Zomato': 'com.application.zomato',
    'Uber Eats': 'com.ubercab.eats',
    'DoorDash': 'com.doordash.consumer.android',
}


def fetch_reviews(app_id: str, lang: str = "en", country: str = "in", count: int = 200):
    """
    Fetch reviews from Google Play Store
    Returns list of review dictionaries with metadata
    """
    try:
        logger.info(f"Fetching {count} reviews for {app_id} ({country}, {lang})")
        data, continuation_token = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=count
        )
        
        # Add review ID and metadata
        for review in data:
            # Use actual Play Store review ID if available, otherwise generate one
            review['review_id'] = review.get('reviewId') or generate_review_id(
                app_id, 
                review.get('content', ''), 
                review.get('reviewCreatedVersion', '')
            )
            review['scraped_at'] = datetime.now().isoformat()
            review['locale'] = f"{lang}_{country.upper()}"
        
        logger.info(f"Successfully fetched {len(data)} reviews for {app_id}")
        return data, continuation_token
        
    except exceptions.NoSuchAppException:
        logger.error(f"App {app_id} not found on Play Store")
        return [], None
    except Exception as e:
        logger.error(f"Error fetching reviews for {app_id}: {e}")
        return [], None


def fetch_reviews_batch(app_ids: List[str], countries: List[str] = None, langs: List[str] = None):
    """
    Fetch reviews for multiple apps and locales
    """
    if countries is None:
        countries = ['us', 'in', 'uk', 'ca', 'au']
    if langs is None:
        langs = ['en']
    
    all_reviews = []
    for app_id in app_ids:
        for country in countries:
            for lang in langs:
                try:
                    reviews_data, _ = fetch_reviews(app_id, lang=lang, country=country)
                    all_reviews.extend(reviews_data)
                except Exception as e:
                    logger.warning(f"Failed to fetch {app_id} for {country}/{lang}: {e}")
    
    return all_reviews


def generate_review_id(app_id: str, content: str, version: str) -> str:
    """Generate unique ID for review to detect duplicates"""
    unique_str = f"{app_id}:{content[:100]}:{version}"
    return hashlib.sha256(unique_str.encode()).hexdigest()[:16]


def parse_review_date(at_value):
    """Parse review timestamp from API output"""
    if isinstance(at_value, datetime):
        return at_value
    try:
        return datetime.fromtimestamp(at_value)
    except Exception:
        return datetime.now()


def normalize_review_for_storage(review: Dict) -> Dict:
    """Convert non-JSON serializable review fields before storing as JSON"""
    normalized = {}
    for k, v in review.items():
        if isinstance(v, datetime):
            normalized[k] = v.isoformat()
        else:
            normalized[k] = v
    return normalized


def fetch_reviews_incremental(app_id: str, days: int = 7):
    """
    Fetch only recent reviews (last N days)
    Useful for incremental processing
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    all_reviews = []
    continuation_token = None
    
    try:
        while True:
            data, continuation_token = reviews(
                app_id,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=100,
                continuation_token=continuation_token
            )
            
            # Filter reviews by date
            recent_reviews = []
            for review in data:
                review_date = datetime.fromtimestamp(review.get('at', 0))
                if review_date >= cutoff_date:
                    review['review_id'] = generate_review_id(
                        app_id, 
                        review.get('content', ''), 
                        review.get('reviewCreatedVersion', '')
                    )
                    recent_reviews.append(review)
                else:
                    # Assuming chronological order, stop if we hit old reviews
                    return all_reviews + recent_reviews
            
            all_reviews.extend(recent_reviews)
            
            if not continuation_token:
                break
                
    except Exception as e:
        logger.error(f"Error in incremental fetch for {app_id}: {e}")
    
    return all_reviews


def validate_review(review: Dict) -> bool:
    """Validate review has required fields"""
    if not review.get('content') or len(review.get('content', '').strip()) < 3:
        return False
    if review.get('score') is None:
        return False
    # Some apps may not always include version metadata
    return True


def fetch_app_rating(app_id: str, lang: str = "en", country: str = "in") -> dict:
    """
    Fetch the actual Play Store app rating and metadata.
    Returns dict with 'score' (overall rating), 'ratings' (count), 'installs', etc.
    """
    try:
        result = gplay_app(app_id, lang=lang, country=country)
        return {
            "score": result.get("score"),           # e.g. 4.2
            "ratings": result.get("ratings"),       # total rating count
            "reviews_count": result.get("reviews"), # total review count
            "installs": result.get("installs"),
            "title": result.get("title"),
        }
    except Exception as e:
        logger.error(f"Error fetching app info for {app_id}: {e}")
        return {}
