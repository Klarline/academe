"""
Authentication endpoints.

Handles user registration, login, token refresh, and password management.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from core.auth.service import AuthService
from core.models import UserProfile
from api.v1.deps import get_auth_service, get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """User login request."""
    email_or_username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    old_password: str
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    Register a new user.
    
    Creates a new user account with the provided credentials.
    Validates email uniqueness, username availability, and password strength.
    
    Args:
        data: Registration data (email, username, password)
        auth_service: Authentication service instance
        
    Returns:
        Created user profile
        
    Raises:
        HTTPException: If validation fails or user already exists
    """
    try:
        user = auth_service.register_user(
            email=data.email,
            username=data.username,
            password=data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
        
        logger.info(f"New user registered: {data.username}")
        return user
        
    except ValueError as e:
        # Validation errors (duplicate email/username, weak password)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    Authenticate user and return JWT token.
    
    Accepts either email or username along with password.
    Returns a JWT token for subsequent authenticated requests.
    
    Args:
        data: Login credentials
        auth_service: Authentication service instance
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    result = auth_service.login_user(
        email_or_username=data.email_or_username,
        password=data.password
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, token = result
    
    logger.info(f"User logged in: {user.username}")
    
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_token: str,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    Refresh an existing JWT token.
    
    Generates a new JWT token if the current token is valid.
    Useful for extending session without re-authentication.
    
    Args:
        current_token: Current valid JWT token
        auth_service: Authentication service instance
        
    Returns:
        New JWT access token
        
    Raises:
        HTTPException: If current token is invalid
    """
    new_token = auth_service.refresh_token(current_token)
    
    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(access_token=new_token)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    Change user password.
    
    Requires current password for verification and new password
    that meets strength requirements.
    
    Args:
        data: Password change data
        current_user_id: ID of authenticated user
        auth_service: Authentication service instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If current password is incorrect or new password is weak
    """
    try:
        success = auth_service.change_password(
            user_id=current_user_id,
            old_password=data.old_password,
            new_password=data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password. Current password may be incorrect."
            )
        
        logger.info(f"Password changed for user: {current_user_id}")
        
        return MessageResponse(message="Password changed successfully")
        
    except ValueError as e:
        # Password validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Logout current user.
    
    In a stateless JWT system, logout is primarily handled client-side
    by discarding the token. This endpoint can be used for logging
    or token blacklisting if implemented.
    
    Args:
        current_user_id: ID of authenticated user
        
    Returns:
        Success message
    """
    logger.info(f"User logged out: {current_user_id}")
    
    return MessageResponse(message="Logged out successfully")


@router.get("/validate")
async def validate_token(
    current_user_id: str = Depends(get_current_user_id)
) -> Any:
    """
    Validate JWT token.
    
    Verifies that the provided token is valid and returns basic user info.
    Useful for client-side token validation.
    
    Args:
        current_user_id: ID extracted from JWT token
        
    Returns:
        Validation status and user ID
    """
    return {
        "valid": True,
        "user_id": current_user_id
    }
