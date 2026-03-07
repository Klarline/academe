"""
Analytics endpoints for RAG performance reports.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.rag.analytics import RAGAnalytics
from api.v1.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/report")
async def get_analytics_report(
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Get RAG analytics report for the authenticated user.

    Returns satisfaction trends, weak documents, query type performance,
    and recommendations. Scoped to user's own feedback data.
    """
    analytics = RAGAnalytics()
    return analytics.generate_report(days=days, user_id=current_user_id)
