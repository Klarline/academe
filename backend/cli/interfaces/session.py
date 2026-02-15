"""Session management for Academe CLI."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.utils.datetime_utils import get_current_time, timedelta
from core.auth import AuthService
from core.database import ConversationRepository, UserRepository
from core.models import Conversation, UserProfile

logger = logging.getLogger(__name__)


class Session:
    """Manages user session state for the CLI."""

    def __init__(self):
        """Initialize session manager."""
        self.auth_service = AuthService()
        self.user_repo = UserRepository()
        self.conv_repo = ConversationRepository()

        # Session state
        self.user: Optional[UserProfile] = None
        self.token: Optional[str] = None
        self.current_conversation: Optional[Conversation] = None

        # Session file for persistence
        self.session_file = Path.home() / ".academe" / "session.json"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing session if available
        self._load_session()

    def login(self, email_or_username: str, password: str) -> bool:
        """
        Authenticate user and start session.

        Args:
            email_or_username: User's email or username
            password: User's password

        Returns:
            True if login successful, False otherwise
        """
        result = self.auth_service.login_user(email_or_username, password)

        if result:
            self.user, self.token = result
            self._save_session()
            logger.info(f"User {self.user.email} logged in successfully")
            return True

        return False

    def logout(self) -> None:
        """End the current session."""
        if self.user:
            logger.info(f"User {self.user.email} logged out")

        self.user = None
        self.token = None
        self.current_conversation = None
        self._clear_session()

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.

        Returns:
            True if user is authenticated and token is valid
        """
        if not self.user or not self.token:
            return False

        # Verify token is still valid
        payload = self.auth_service.verify_jwt_token(self.token)
        if not payload:
            # Token expired or invalid
            self.logout()
            return False

        return True

    def refresh_session(self) -> bool:
        """
        Refresh the current session token.

        Returns:
            True if refresh successful
        """
        if not self.token:
            return False

        new_token = self.auth_service.refresh_token(self.token)
        if new_token:
            self.token = new_token
            self._save_session()
            return True

        return False

    def create_new_conversation(self, title: Optional[str] = None) -> str:
        """
        Create a new conversation for the current user.

        Args:
            title: Optional conversation title

        Returns:
            Conversation ID

        Raises:
            RuntimeError: If user not authenticated
        """
        if not self.user:
            raise RuntimeError("User must be authenticated to create conversation")

        # Generate title if not provided
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Create conversation
        conv_id = self.conv_repo.create_conversation(
            user_id=self.user.id,
            title=title
        )

        # Load as current conversation
        self.current_conversation = self.conv_repo.get_conversation(conv_id)

        logger.info(f"Created new conversation: {conv_id}")
        return conv_id

    def load_conversation(self, conversation_id: str) -> bool:
        """
        Load an existing conversation.

        Args:
            conversation_id: ID of conversation to load

        Returns:
            True if loaded successfully

        Raises:
            RuntimeError: If user not authenticated
        """
        if not self.user:
            raise RuntimeError("User must be authenticated to load conversation")

        conversation = self.conv_repo.get_conversation(conversation_id)

        if conversation and conversation.user_id == self.user.id:
            self.current_conversation = conversation
            logger.info(f"Loaded conversation: {conversation_id}")
            return True

        logger.warning(f"Failed to load conversation: {conversation_id}")
        return False

    def get_or_create_conversation(self) -> Conversation:
        """
        Get current conversation or create a new one.

        Returns:
            Current conversation
        """
        if not self.current_conversation:
            self.create_new_conversation()

        return self.current_conversation

    def _save_session(self) -> None:
        """Save session data to file."""
        if not self.token:
            return

        try:
            session_data = {
                "token": self.token,
                "user_id": self.user.id if self.user else None,
                "email": self.user.email if self.user else None,
                "conversation_id": self.current_conversation.id if self.current_conversation else None,
                "saved_at": get_current_time().isoformat()
            }

            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            # Set file permissions to be readable only by owner
            os.chmod(self.session_file, 0o600)

        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def _load_session(self) -> None:
        """Load session data from file."""
        if not self.session_file.exists():
            return

        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)

            # Check if session is not too old (24 hours)
            saved_at = datetime.fromisoformat(session_data.get("saved_at", ""))
            if get_current_time() - saved_at > timedelta(hours=24):
                logger.info("Session expired, clearing")
                self._clear_session()
                return

            # Verify token
            token = session_data.get("token")
            if token:
                user = self.auth_service.get_user_from_token(token)
                if user:
                    self.token = token
                    self.user = user

                    # Try to load last conversation
                    conv_id = session_data.get("conversation_id")
                    if conv_id:
                        self.load_conversation(conv_id)

                    logger.info(f"Restored session for user: {user.email}")
                else:
                    self._clear_session()

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            self._clear_session()

    def _clear_session(self) -> None:
        """Clear saved session data."""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
        except Exception as e:
            logger.error(f"Failed to clear session file: {e}")

    def update_user_preferences(self, preferences: dict) -> bool:
        """
        Update current user's preferences.

        Args:
            preferences: Dictionary of preferences to update

        Returns:
            True if updated successfully
        """
        if not self.user:
            return False

        success = self.user_repo.update_user(self.user.id, preferences)

        if success:
            # Update local user object
            for key, value in preferences.items():
                if hasattr(self.user, key):
                    setattr(self.user, key, value)

        return success

    def get_session_info(self) -> dict:
        """
        Get current session information.

        Returns:
            Dictionary with session details
        """
        return {
            "authenticated": self.is_authenticated(),
            "user": {
                "id": self.user.id if self.user else None,
                "email": self.user.email if self.user else None,
                "username": self.user.username if self.user else None,
                "learning_level": self.user.learning_level.value if self.user else None,
                "learning_goal": self.user.learning_goal.value if self.user else None,
                "explanation_style": self.user.explanation_style.value if self.user else None,
            } if self.user else None,
            "conversation": {
                "id": self.current_conversation.id if self.current_conversation else None,
                "title": self.current_conversation.title if self.current_conversation else None,
                "message_count": self.current_conversation.message_count if self.current_conversation else 0,
            } if self.current_conversation else None,
        }

    def __repr__(self) -> str:
        """String representation."""
        if self.user:
            return f"<Session user={self.user.email} authenticated=True>"
        return "<Session authenticated=False>"