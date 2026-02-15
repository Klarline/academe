"""Authentication service for Academe."""

import logging
from datetime import timedelta
from typing import Optional, Tuple

import bcrypt
from jose import JWTError, jwt

from core.config.settings import get_settings
from core.database import UserRepository
from core.models import UserProfile
from core.utils import get_current_time

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication and authorization."""

    def __init__(self):
        """Initialize authentication service."""
        self.settings = get_settings()
        self.user_repo = UserRepository()
        self.secret_key = self.settings.jwt_secret_key
        self.algorithm = self.settings.jwt_algorithm
        self.expiration_hours = self.settings.jwt_expiration_hours

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        # Generate salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password
            hashed: Hashed password to check against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def create_jwt_token(self, user_id: str, email: str) -> str:
        """
        Create a JWT token for a user.

        Args:
            user_id: User's ID
            email: User's email

        Returns:
            JWT token string
        """
        # Calculate expiration time
        expire = get_current_time() + timedelta(hours=self.expiration_hours)

        # Create token payload
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "exp": expire,
            "iat": get_current_time(),
            "type": "access"
        }

        # Encode token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_jwt_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    def register_user(
        self,
        email: str,
        username: str,
        password: str
    ) -> Optional[UserProfile]:
        """
        Register a new user.

        Args:
            email: User's email
            username: User's username
            password: Plain text password

        Returns:
            Created UserProfile if successful, None otherwise

        Raises:
            ValueError: If user already exists or validation fails
        """
        try:
            # Check if user already exists
            existing_user = self.user_repo.get_user_by_email(email)
            if existing_user:
                raise ValueError(f"User with email {email} already exists")

            # Check username availability
            existing_username = self.user_repo.get_user_by_username(username)
            if existing_username:
                raise ValueError(f"Username {username} is already taken")

            # Validate password strength
            is_valid, message = self.validate_password_strength(password)
            if not is_valid:
                raise ValueError(message)

            # Hash password
            password_hash = self.hash_password(password)

            # Create user profile
            user = UserProfile(
                email=email.lower(),
                username=username.lower(),
                password_hash=password_hash,
                has_completed_onboarding=False
            )

            # Save to database
            user_id = self.user_repo.create_user(user)
            user.id = user_id

            logger.info(f"Successfully registered user: {email}")
            return user

        except ValueError as e:
            logger.error(f"Registration validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            return None

    def login_user(
        self,
        email_or_username: str,
        password: str
    ) -> Optional[Tuple[UserProfile, str]]:
        """
        Authenticate a user and generate token.

        Args:
            email_or_username: User's email or username
            password: Plain text password

        Returns:
            Tuple of (UserProfile, JWT token) if successful, None otherwise
        """
        try:
            # Try to find user by email first
            user = self.user_repo.get_user_by_email(email_or_username.lower())

            # If not found by email, try username
            if not user:
                user = self.user_repo.get_user_by_username(email_or_username.lower())

            # Check if user exists
            if not user:
                logger.warning(f"Login attempt for non-existent user: {email_or_username}")
                return None

            # Verify password
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Invalid password for user: {email_or_username}")
                return None

            # Check if user is active
            if not user.is_active:
                logger.warning(f"Login attempt for inactive user: {email_or_username}")
                return None

            # Generate JWT token
            token = self.create_jwt_token(user.id, user.email)

            # Update last login timestamp
            self.user_repo.update_last_login(user.id)

            logger.info(f"User logged in successfully: {user.email}")
            return (user, token)

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None

    def get_user_from_token(self, token: str) -> Optional[UserProfile]:
        """
        Get user profile from JWT token.

        Args:
            token: JWT token string

        Returns:
            UserProfile if token is valid, None otherwise
        """
        payload = self.verify_jwt_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return self.user_repo.get_user_by_id(user_id)

    def refresh_token(self, token: str) -> Optional[str]:
        """
        Refresh an existing JWT token.

        Args:
            token: Current JWT token

        Returns:
            New JWT token if successful, None otherwise
        """
        payload = self.verify_jwt_token(token)
        if not payload:
            return None

        # Create new token with same user info
        return self.create_jwt_token(
            payload.get("sub"),
            payload.get("email")
        )

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change a user's password.

        Args:
            user_id: User's ID
            old_password: Current password
            new_password: New password

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return False

            # Verify old password
            if not self.verify_password(old_password, user.password_hash):
                logger.warning(f"Invalid old password for user {user_id}")
                return False

            # Validate new password
            is_valid, message = self.validate_password_strength(new_password)
            if not is_valid:
                raise ValueError(message)

            # Hash new password
            new_hash = self.hash_password(new_password)

            # Update in database
            return self.user_repo.update_user(
                user_id,
                {"password_hash": new_hash}
            )

        except Exception as e:
            logger.error(f"Failed to change password: {e}")
            return False

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"

        return True, "Password is strong"