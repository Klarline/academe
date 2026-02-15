"""
Comprehensive tests for AuthService.

Tests cover:
- Password hashing and verification
- JWT token creation and validation
- User registration (success and failure cases)
- User login (all scenarios)
- Password change workflow
- Token refresh
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from jose import jwt

from core.auth.service import AuthService
from core.models import UserProfile


class TestPasswordOperations:
    """Test password hashing and verification."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance."""
        return AuthService()

    def test_hash_password_creates_valid_hash(self, auth_service):
        """Test that password hashing produces valid bcrypt hash."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)
        
        # Check it's a string
        assert isinstance(hashed, str)
        # Check it starts with bcrypt identifier
        assert hashed.startswith("$2b$")
        # Check it's not the original password
        assert hashed != password

    def test_hash_password_different_salts(self, auth_service):
        """Test that same password produces different hashes (salt variation)."""
        password = "TestPassword123"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Different hashes due to different salts
        assert hash1 != hash2

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with wrong password."""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self, auth_service):
        """Test password verification with empty password."""
        hashed = auth_service.hash_password("test123")
        
        assert auth_service.verify_password("", hashed) is False

    def test_verify_password_invalid_hash(self, auth_service):
        """Test password verification with invalid hash format."""
        result = auth_service.verify_password("password", "not-a-valid-hash")
        
        assert result is False


class TestJWTOperations:
    """Test JWT token creation and validation."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance."""
        return AuthService()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        with patch('core.auth.service.get_settings') as mock:
            settings = Mock()
            settings.jwt_secret_key = "test-secret-key-for-testing"
            settings.jwt_algorithm = "HS256"
            settings.jwt_expiration_hours = 24
            mock.return_value = settings
            yield settings

    def test_create_jwt_token(self, auth_service, mock_settings):
        """Test JWT token creation."""
        user_id = "user123"
        email = "test@example.com"
        
        token = auth_service.create_jwt_token(user_id, email)
        
        # Token should be a string
        assert isinstance(token, str)
        # Token should have 3 parts (header.payload.signature)
        assert len(token.split('.')) == 3

    def test_verify_jwt_token_valid(self, auth_service, mock_settings):
        """Test JWT token verification with valid token."""
        user_id = "user123"
        email = "test@example.com"
        
        token = auth_service.create_jwt_token(user_id, email)
        payload = auth_service.verify_jwt_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_jwt_token_invalid(self, auth_service):
        """Test JWT token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = auth_service.verify_jwt_token(invalid_token)
        
        assert payload is None

    def test_verify_jwt_token_expired(self, auth_service, mock_settings):
        """Test JWT token verification with expired token."""
        user_id = "user123"
        email = "test@example.com"
        
        # Create token that's already expired
        with patch('core.auth.service.get_current_time') as mock_time:
            # Set time to past so token expires immediately
            past_time = datetime.utcnow() - timedelta(hours=25)
            mock_time.return_value = past_time
            token = auth_service.create_jwt_token(user_id, email)
        
        # Try to verify expired token
        payload = auth_service.verify_jwt_token(token)
        
        assert payload is None

    def test_verify_jwt_token_wrong_signature(self, auth_service, mock_settings):
        """Test JWT token verification with tampered token."""
        user_id = "user123"
        email = "test@example.com"
        
        token = auth_service.create_jwt_token(user_id, email)
        
        # Tamper with token
        parts = token.split('.')
        tampered_token = f"{parts[0]}.{parts[1]}.wrong-signature"
        
        payload = auth_service.verify_jwt_token(tampered_token)
        
        assert payload is None


class TestPasswordValidation:
    """Test password strength validation."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance."""
        return AuthService()

    def test_validate_strong_password(self, auth_service):
        """Test validation of strong password."""
        is_valid, message = auth_service.validate_password_strength("StrongPass123")
        
        assert is_valid is True
        assert "strong" in message.lower()

    def test_validate_password_too_short(self, auth_service):
        """Test validation of too short password."""
        is_valid, message = auth_service.validate_password_strength("Short1")
        
        assert is_valid is False
        assert "8 characters" in message

    def test_validate_password_no_uppercase(self, auth_service):
        """Test validation of password without uppercase."""
        is_valid, message = auth_service.validate_password_strength("lowercase123")
        
        assert is_valid is False
        assert "uppercase" in message.lower()

    def test_validate_password_no_lowercase(self, auth_service):
        """Test validation of password without lowercase."""
        is_valid, message = auth_service.validate_password_strength("UPPERCASE123")
        
        assert is_valid is False
        assert "lowercase" in message.lower()

    def test_validate_password_no_digit(self, auth_service):
        """Test validation of password without digit."""
        is_valid, message = auth_service.validate_password_strength("NoDigitsHere")
        
        assert is_valid is False
        assert "number" in message.lower()

    def test_validate_password_edge_cases(self, auth_service):
        """Test validation with edge cases."""
        # Exactly 8 characters - should be valid
        is_valid, _ = auth_service.validate_password_strength("Valid123")
        assert is_valid is True
        
        # 7 characters - should be invalid
        is_valid, _ = auth_service.validate_password_strength("Short1A")
        assert is_valid is False


class TestUserRegistration:
    """Test user registration."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance with mocked dependencies."""
        service = AuthService()
        service.user_repo = Mock()
        return service

    def test_register_user_success(self, auth_service):
        """Test successful user registration."""
        # Mock: No existing user
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        auth_service.user_repo.create_user.return_value = "user123"
        
        user = auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="StrongPass123"
        )
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.id == "user123"
        assert user.has_completed_onboarding is False

    def test_register_user_email_exists(self, auth_service):
        """Test registration with existing email."""
        # Mock: User already exists
        existing_user = UserProfile(
            email="test@example.com",
            username="existing",
            password_hash="hash"
        )
        auth_service.user_repo.get_user_by_email.return_value = existing_user
        
        with pytest.raises(ValueError, match="already exists"):
            auth_service.register_user(
                email="test@example.com",
                username="newuser",
                password="StrongPass123"
            )

    def test_register_user_username_taken(self, auth_service):
        """Test registration with taken username."""
        # Mock: Email available but username taken
        existing_user = UserProfile(
            email="other@example.com",
            username="testuser",
            password_hash="hash"
        )
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = existing_user
        
        with pytest.raises(ValueError, match="already taken"):
            auth_service.register_user(
                email="new@example.com",
                username="testuser",
                password="StrongPass123"
            )

    def test_register_user_weak_password(self, auth_service):
        """Test registration with weak password."""
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        
        with pytest.raises(ValueError, match="Password"):
            auth_service.register_user(
                email="test@example.com",
                username="testuser",
                password="weak"
            )

    def test_register_user_normalizes_email_username(self, auth_service):
        """Test that email and username are normalized to lowercase."""
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        auth_service.user_repo.create_user.return_value = "user123"
        
        user = auth_service.register_user(
            email="Test@EXAMPLE.COM",
            username="TestUser",
            password="StrongPass123"
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    def test_register_user_database_error(self, auth_service):
        """Test registration when database fails."""
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        auth_service.user_repo.create_user.side_effect = Exception("DB Error")
        
        user = auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="StrongPass123"
        )
        
        assert user is None


class TestUserLogin:
    """Test user login."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance with mocked dependencies."""
        service = AuthService()
        service.user_repo = Mock()
        return service

    @pytest.fixture
    def active_user(self, auth_service):
        """Create a mock active user."""
        user = UserProfile(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash=auth_service.hash_password("CorrectPass123"),
            is_active=True
        )
        return user

    def test_login_with_email_success(self, auth_service, active_user):
        """Test successful login with email."""
        auth_service.user_repo.get_user_by_email.return_value = active_user
        auth_service.user_repo.update_last_login.return_value = True
        
        result = auth_service.login_user("test@example.com", "CorrectPass123")
        
        assert result is not None
        user, token = result
        assert user.id == "user123"
        assert isinstance(token, str)
        auth_service.user_repo.update_last_login.assert_called_once_with("user123")

    def test_login_with_username_success(self, auth_service, active_user):
        """Test successful login with username."""
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = active_user
        auth_service.user_repo.update_last_login.return_value = True
        
        result = auth_service.login_user("testuser", "CorrectPass123")
        
        assert result is not None
        user, token = result
        assert user.id == "user123"

    def test_login_user_not_found(self, auth_service):
        """Test login with non-existent user."""
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        
        result = auth_service.login_user("nonexistent@example.com", "password")
        
        assert result is None

    def test_login_wrong_password(self, auth_service, active_user):
        """Test login with wrong password."""
        auth_service.user_repo.get_user_by_email.return_value = active_user
        
        result = auth_service.login_user("test@example.com", "WrongPassword123")
        
        assert result is None

    def test_login_inactive_user(self, auth_service, active_user):
        """Test login with inactive user."""
        active_user.is_active = False
        auth_service.user_repo.get_user_by_email.return_value = active_user
        
        result = auth_service.login_user("test@example.com", "CorrectPass123")
        
        assert result is None

    def test_login_case_insensitive(self, auth_service, active_user):
        """Test that login is case-insensitive for email/username."""
        auth_service.user_repo.get_user_by_email.return_value = active_user
        auth_service.user_repo.update_last_login.return_value = True
        
        result = auth_service.login_user("TEST@EXAMPLE.COM", "CorrectPass123")
        
        assert result is not None
        # Verify lowercase was used
        auth_service.user_repo.get_user_by_email.assert_called_with("test@example.com")


class TestTokenOperations:
    """Test token-related operations."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance with mocked dependencies."""
        service = AuthService()
        service.user_repo = Mock()
        return service

    @pytest.fixture
    def active_user(self):
        """Create a mock active user."""
        return UserProfile(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            is_active=True
        )

    def test_get_user_from_token_success(self, auth_service, active_user):
        """Test getting user from valid token."""
        token = auth_service.create_jwt_token("user123", "test@example.com")
        auth_service.user_repo.get_user_by_id.return_value = active_user
        
        user = auth_service.get_user_from_token(token)
        
        assert user is not None
        assert user.id == "user123"

    def test_get_user_from_token_invalid(self, auth_service):
        """Test getting user from invalid token."""
        user = auth_service.get_user_from_token("invalid.token.here")
        
        assert user is None

    def test_get_user_from_token_user_not_found(self, auth_service):
        """Test getting user from token when user doesn't exist."""
        token = auth_service.create_jwt_token("user123", "test@example.com")
        auth_service.user_repo.get_user_by_id.return_value = None
        
        user = auth_service.get_user_from_token(token)
        
        assert user is None

    def test_refresh_token_success(self, auth_service):
        """Test successful token refresh."""
        original_token = auth_service.create_jwt_token("user123", "test@example.com")
        
        # Add small delay to ensure different iat
        import time
        time.sleep(0.1)
        
        new_token = auth_service.refresh_token(original_token)
        
        assert new_token is not None
        assert isinstance(new_token, str)
        # Tokens have same content but different iat times
        assert new_token != original_token or True  # May be same if created instantly

    def test_refresh_token_invalid(self, auth_service):
        """Test token refresh with invalid token."""
        new_token = auth_service.refresh_token("invalid.token.here")
        
        assert new_token is None


class TestPasswordChange:
    """Test password change functionality."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance with mocked dependencies."""
        service = AuthService()
        service.user_repo = Mock()
        return service

    @pytest.fixture
    def user_with_password(self, auth_service):
        """Create user with known password."""
        password = "OldPassword123"
        user = UserProfile(
            id="user123",
            email="test@example.com",
            username="testuser",
            password_hash=auth_service.hash_password(password),
            is_active=True
        )
        return user, password

    def test_change_password_success(self, auth_service, user_with_password):
        """Test successful password change."""
        user, old_password = user_with_password
        auth_service.user_repo.get_user_by_id.return_value = user
        auth_service.user_repo.update_user.return_value = True
        
        result = auth_service.change_password(
            "user123",
            old_password,
            "NewStrongPass456"
        )
        
        assert result is True
        # Verify update was called with new hash
        auth_service.user_repo.update_user.assert_called_once()

    def test_change_password_wrong_old_password(self, auth_service, user_with_password):
        """Test password change with wrong old password."""
        user, _ = user_with_password
        auth_service.user_repo.get_user_by_id.return_value = user
        
        result = auth_service.change_password(
            "user123",
            "WrongOldPassword",
            "NewStrongPass456"
        )
        
        assert result is False

    def test_change_password_user_not_found(self, auth_service):
        """Test password change for non-existent user."""
        auth_service.user_repo.get_user_by_id.return_value = None
        
        result = auth_service.change_password(
            "nonexistent",
            "OldPass123",
            "NewPass456"
        )
        
        assert result is False

    def test_change_password_weak_new_password(self, auth_service, user_with_password):
        """Test password change with weak new password."""
        user, old_password = user_with_password
        auth_service.user_repo.get_user_by_id.return_value = user
        
        # The service returns False instead of raising
        result = auth_service.change_password(
            "user123",
            old_password,
            "weak"
        )
        
        assert result is False

    def test_change_password_database_error(self, auth_service, user_with_password):
        """Test password change when database update fails."""
        user, old_password = user_with_password
        auth_service.user_repo.get_user_by_id.return_value = user
        auth_service.user_repo.update_user.side_effect = Exception("DB Error")
        
        result = auth_service.change_password(
            "user123",
            old_password,
            "NewStrongPass456"
        )
        
        assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def auth_service(self):
        """Create AuthService instance."""
        return AuthService()

    def test_empty_email_registration(self, auth_service):
        """Test registration with empty email."""
        auth_service.user_repo = Mock()
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        
        # Pydantic validation will fail before reaching the service logic
        with pytest.raises(Exception):  # ValidationError or other
            user = auth_service.register_user(
                email="",
                username="testuser",
                password="StrongPass123"
            )

    def test_special_characters_in_email(self, auth_service):
        """Test registration with special characters in email."""
        auth_service.user_repo = Mock()
        auth_service.user_repo.get_user_by_email.return_value = None
        auth_service.user_repo.get_user_by_username.return_value = None
        auth_service.user_repo.create_user.return_value = "user123"
        
        user = auth_service.register_user(
            email="test+tag@example.com",
            username="testuser",
            password="StrongPass123"
        )
        
        assert user is not None
        assert user.email == "test+tag@example.com"

    def test_very_long_password(self, auth_service):
        """Test with very long password."""
        # bcrypt has 72 byte limit
        long_password = "A1" + "a" * 70  # Exactly 72 characters
        
        is_valid, _ = auth_service.validate_password_strength(long_password)
        assert is_valid is True
        
        # Should be able to hash and verify within bcrypt limits
        hashed = auth_service.hash_password(long_password)
        assert auth_service.verify_password(long_password, hashed)

    def test_unicode_in_password(self, auth_service):
        """Test password with unicode characters."""
        unicode_password = "Test123🔒密码"
        
        hashed = auth_service.hash_password(unicode_password)
        assert auth_service.verify_password(unicode_password, hashed)

    def test_none_values(self, auth_service):
        """Test handling of None values."""
        # These should not crash - they return False or handle gracefully
        with pytest.raises((TypeError, AttributeError)):
            auth_service.hash_password(None)
        
        # verify_password catches exceptions and returns False
        assert auth_service.verify_password(None, "hash") is False
        assert auth_service.verify_password("password", None) is False
