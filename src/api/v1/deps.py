"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection for JWT validation, user authentication,
and database access throughout the API.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.auth.service import AuthService
from core.models import UserProfile
from core.database.connection import get_database

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Initialize services
auth_service = AuthService()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and validate user ID from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    # Verify token using AuthService
    payload = auth_service.verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id)
) -> UserProfile:
    """
    Get current authenticated user profile.
    
    Args:
        user_id: User ID from JWT token
        
    Returns:
        UserProfile instance
        
    Raises:
        HTTPException: If user not found
    """
    user = auth_service.user_repo.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[str]:
    """
    Get user ID from token if provided, otherwise return None.
    
    Useful for endpoints that work with or without authentication.
    
    Args:
        credentials: Optional HTTP Bearer token
        
    Returns:
        User ID if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = auth_service.verify_jwt_token(token)
        
        if payload:
            return payload.get("sub")
    except Exception as e:
        logger.warning(f"Invalid token provided: {e}")
    
    return None


def get_auth_service() -> AuthService:
    """
    Get AuthService instance.
    
    Returns:
        Configured AuthService
    """
    return auth_service


def get_db():
    """
    Get database instance.
    
    Returns:
        Database connection
    """
    return get_database()
