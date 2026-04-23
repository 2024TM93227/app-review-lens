"""Responsible AI policy API."""
from fastapi import APIRouter

from app.services.responsible_ai import policy_manifest

router = APIRouter()


@router.get("/responsible-ai")
def get_responsible_ai_policy():
    return policy_manifest()
