"""
AI suggestion API router.
POST /suggest accepts a payload (comparison, top_issues, trends) and returns LLM-generated suggestions.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import logging

from app.services.ai import generate_suggestions

logger = logging.getLogger(__name__)

router = APIRouter()


class SuggestRequest(BaseModel):
    payload: Dict[str, Any]
    model: Optional[str] = 'gpt-3.5-turbo'


class SuggestResponse(BaseModel):
    summary: Any
    action_items: Any
    release_notes: Any
    experiment: Any


@router.post('/suggest', response_model=SuggestResponse)
def suggest(req: SuggestRequest):
    try:
        suggestions = generate_suggestions(req.payload, model=req.model)
        # If the LLM returns strings or different shape, normalize in the service
        return suggestions
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.exception('AI suggestion failed')
        raise HTTPException(status_code=500, detail='AI suggestion failed')
