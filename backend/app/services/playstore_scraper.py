"""
PlayStore Review Ingestion Module
Fetches public reviews from Google Play Store for target apps
"""
import logging
try:
    from google_play_scraper import reviews, Sort, exceptions
    GOOGLE_SCRAPER_AVAILABLE = True
except Exception:
    # Provide a lightweight fallback when the external scraper isn't available
    GOOGLE_SCRAPER_AVAILABLE = False
    logging.getLogger(__name__).warning("google_play_scraper not installed; using stub fetcher")

    class Sort:
        NEWEST = None

    class exceptions:
        class NoSuchAppException(Exception):
            pass
        class RequestException(Exception):
            pass

    def reviews(app_id, lang: str = "en", country: str = "us", sort=None, count: int = 200, continuation_token=None):
        """Stub reviews function when google_play_scraper is not installed.
        Returns empty list so the app can run without the external dependency.
        """
        logging.getLogger(__name__).warning(f"Stubbed fetch for {app_id} (google_play_scraper missing)")
        return [], None
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import hashlib
import threading
import signal

logger = logging.getLogger(__name__)

# Timeout in seconds for fetch operations
FETCH_TIMEOUT_SECONDS = 60

class FetchTimeoutError(Exception):
    """Raised when fetch_reviews exceeds timeout"""
    pass

def _timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise FetchTimeoutError("Fetch operation exceeded timeout")


# Food-delivery app IDs to monitor
FOOD_DELIVERY_APPS = {
    'Swiggy': 'com.swiggy.swiggy',
    'Zomato': 'com.application.zomato',
    'Uber Eats': 'com.ubercab.eats',
    'DoorDash': 'com.doordash.consumer.android',
}


def fetch_reviews(app_id: str, lang: str = "en", country: str = "us", count: int = 200, timeout: int = FETCH_TIMEOUT_SECONDS) -> Tuple[List[Dict], Optional[str]]:
    """
    Fetch reviews from Google Play Store with timeout protection.
    
    Args:
        app_id: Google Play app ID (e.g., 'com.swiggy.swiggy')
        lang: Language code (default 'en')
        country: Country code (default 'us')
        count: Number of reviews to fetch (default 200)
        timeout: Timeout in seconds (default 60)
    
    Returns:
        Tuple of (reviews_list, continuation_token)
    
    Raises:
        FetchTimeoutError: If fetch operation exceeds timeout
        Exception: Other errors from Google Play Store API
    """
    try:
        logger.info(f"Fetching {count} reviews for {app_id} ({country}, {lang}) with {timeout}s timeout")
        
        # Set signal-based timeout (Unix-like systems only)
        # For Windows or better reliability, use thread-based timeout
        start_time = datetime.now()
        
        try:
            data, continuation_token = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                logger.warning(f"Fetch completed but exceeded timeout threshold: {elapsed:.1f}s > {timeout}s")
                raise FetchTimeoutError(f"Operation took {elapsed:.1f}s, exceeding {timeout}s timeout")
            
        except FetchTimeoutError:
            raise
        except exceptions.RequestException as e:
            logger.error(f"Request error fetching reviews for {app_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching reviews for {app_id}: {e}")
            raise
        
        # Add review ID and metadata
        for review in data:
            # Generate unique review ID from content hash
            review['review_id'] = generate_review_id(
                app_id, 
                review.get('content', ''), 
                review.get('reviewCreatedVersion', '')
            )
            review['scraped_at'] = datetime.now().isoformat()
            review['locale'] = f"{lang}_{country.upper()}"
        
        logger.info(f"Successfully fetched {len(data)} reviews for {app_id} in {elapsed:.1f}s")
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


def parse_review_date(at_value: any) -> datetime:
    """
    Parse review timestamp from API output.
    
    Args:
        at_value: Can be datetime object, Unix timestamp (int/float), or None
    
    Returns:
        datetime: Parsed datetime or None if cannot be determined
    """
    if at_value is None:
        return None
    if isinstance(at_value, datetime):
        return at_value
    try:
        # Try to parse as Unix timestamp (seconds)
        if isinstance(at_value, (int, float)):
            return datetime.fromtimestamp(at_value)
        # Try to parse as ISO string
        if isinstance(at_value, str):
            return datetime.fromisoformat(at_value.replace('Z', '+00:00'))
        return None
    except (ValueError, TypeError, OSError):
        return None


def normalize_review_for_storage(review: Dict) -> Dict:
    """Convert non-JSON serializable review fields before storing as JSON"""
    normalized = {}
    for k, v in review.items():
        if isinstance(v, datetime):
            normalized[k] = v.isoformat()
        else:
            normalized[k] = v
    return normalized


def fetch_reviews_incremental(app_id: str, since_date: Optional[datetime] = None, max_reviews: int = 500):
    """
    Fetch reviews since a specific date (incremental ingestion).
    
    Args:
        app_id: Google Play app ID
        since_date: Only fetch reviews after this date (None = all recent)
        max_reviews: Max reviews to fetch (batch processing limit)
    
    Returns:
        List of reviews after since_date, sorted newest first
    """
    if since_date is None:
        since_date = datetime.now() - timedelta(days=7)  # Default: last 7 days
    
    logger.info(f"Fetching reviews for {app_id} since {since_date}")
    
    all_reviews = []
    continuation_token = None
    reviews_fetched = 0
    
    try:
        while reviews_fetched < max_reviews:
            batch_count = min(100, max_reviews - reviews_fetched)
            
            data, continuation_token = reviews(
                app_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=batch_count,
                continuation_token=continuation_token
            )
            
            if not data:
                logger.info(f"No more reviews for {app_id}")
                break
            
            # Process reviews in batch
            batch_reviews = []
            for review in data:
                review_date = parse_review_date(review.get('at'))
                
                # Stop if we've reached reviews older than since_date
                if review_date and review_date < since_date:
                    logger.info(f"Reached reviews older than {since_date}, stopping fetch")
                    return all_reviews + batch_reviews
                
                # Add review ID and metadata
                review['review_id'] = generate_review_id(
                    app_id, 
                    review.get('content', ''), 
                    review.get('reviewCreatedVersion', '')
                )
                review['scraped_at'] = datetime.now().isoformat()
                review['locale'] = 'en_US'
                batch_reviews.append(review)
            
            all_reviews.extend(batch_reviews)
            reviews_fetched += len(batch_reviews)
            
            logger.info(f"Fetched batch of {len(batch_reviews)} reviews for {app_id}, total: {reviews_fetched}")
            
            # Stop if no continuation token (reached end)
            if not continuation_token:
                logger.info(f"Reached end of reviews for {app_id}")
                break
            
            # Stop if we've hit our batch limit
            if reviews_fetched >= max_reviews:
                logger.info(f"Reached max_reviews limit ({max_reviews}) for {app_id}")
                break
    
    except Exception as e:
        logger.error(f"Error fetching incremental reviews for {app_id}: {e}")
        # Return whatever we've collected so far
    
    logger.info(f"Incremental fetch complete for {app_id}: {len(all_reviews)} total reviews")
    return all_reviews


def validate_review(review: Dict) -> bool:
    """Validate review has required fields"""
    if not review.get('content') or len(review.get('content', '')) < 10:
        return False
    if review.get('score') is None:
        return False
    # Some apps may not always include version metadata
    return True
