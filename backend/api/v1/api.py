"""
API v1 router aggregator.

Combines all v1 endpoint routers into a single router for the application.
"""

from fastapi import APIRouter

from api.v1.endpoints import (
    auth,
    users,
    chat,
    documents,
    progress,
    websocket,
    practice,
    research
)

# Create API router
api_router = APIRouter()

# Include all endpoint routers with appropriate prefixes and tags
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

api_router.include_router(
    progress.router,
    prefix="/progress",
    tags=["progress"]
)

api_router.include_router(
    websocket.router,
    prefix="/ws",
    tags=["websocket"]
)

api_router.include_router(
    practice.router,
    prefix="/practice",
    tags=["practice"]
)

api_router.include_router(
    research.router,
    prefix="/research",
    tags=["research"]
)
