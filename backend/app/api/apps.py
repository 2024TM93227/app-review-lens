"""
App Discovery API Module
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from app.api.schemas import AppSearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Mock data for app discovery - in production this would query Google Play API
FOOD_DELIVERY_APPS = [
    {
        "app_id": "in.swiggy.android",
        "name": "Swiggy",
        "category": "food_delivery",
        "rating": 4.2,
        "review_count": 2150000,
        "icon_url": "https://play-lh.googleusercontent.com/dJ3oHEeYIMj9rMqQLLtQ0V4VD1W2PGHdJXY7qYIYJhKL18AAVGKq8F0PZo7n6kRQA"
    },
    {
        "app_id": "com.application.zomato",
        "name": "Zomato",
        "category": "food_delivery",
        "rating": 4.3,
        "review_count": 1890000,
        "icon_url": "https://play-lh.googleusercontent.com/L3bXBxCBKqY8v0vYyiMdKqjuV3Iy6qk9XZtO6Rh_W6oCT9S3VvIIpLvGvmVhCLkQ"
    },
    {
        "app_id": "com.ubercab.eats",
        "name": "Uber Eats",
        "category": "food_delivery",
        "rating": 4.1,
        "review_count": 987000,
        "icon_url": "https://play-lh.googleusercontent.com/JEjVPpPEPL0N1yUY0LAK2SFAMqvYHBm8JKzN7PU4BrGpgXUaXQ5PlVaXBv5aXVLM"
    },
    {
        "app_id": "in.swiggy.android.instamart",
        "name": "Swiggy Instamart",
        "category": "food_delivery",
        "rating": 4.0,
        "review_count": 456000,
        "icon_url": "https://play-lh.googleusercontent.com/WbJ8SPkrQaQRPuXFSpRlKh2BgzkItf3uL4ck0Z43Pn8lZVBaVsKGaQMJvRPGRQ7hQ"
    },
    {
        "app_id": "com.ola.one",
        "name": "Ola Food",
        "category": "food_delivery",
        "rating": 3.9,
        "review_count": 234000,
        "icon_url": "https://play-lh.googleusercontent.com/Dh3WBBNUUj2blDm5qN5RxAVCCNfDf3Uv9xM_ZrtPtpwOCEqD5fJxcVVPVB9hQ"
    }
]


@router.get("/search", response_model=List[AppSearchResponse])
def search_apps(
    q: str = Query("", description="Search query"),
    category: str = Query("food_delivery", description="App category"),
    limit: int = Query(20, le=100, description="Max results")
):
    """
    Search and discover apps on Google Play Store.
    
    Supports filtering by category and search term.
    Returns app metadata: ID, name, rating, review count.
    """
    results = FOOD_DELIVERY_APPS
    
    if q:
        q_lower = q.lower()
        results = [app for app in results if q_lower in app["name"].lower()]
    
    results = [app for app in results if app["category"] == category]
    
    return results[:limit]


@router.get("/{app_id}", response_model=AppSearchResponse)
def get_app_details(app_id: str):
    """
    Get detailed information about a specific app.
    """
    for app in FOOD_DELIVERY_APPS:
        if app["app_id"] == app_id:
            return app
    
    raise HTTPException(status_code=404, detail="App not found")
