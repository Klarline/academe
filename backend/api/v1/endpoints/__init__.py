"""
API v1 endpoints.

All endpoint modules for version 1 of the API.
"""

from . import auth
from . import users
from . import chat
from . import documents
from . import progress
from . import websocket
from . import practice
from . import research

__all__ = [
    "auth",
    "users",
    "chat",
    "documents",
    "progress",
    "websocket",
    "practice",
    "research",
]
