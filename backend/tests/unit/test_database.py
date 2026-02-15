"""
Comprehensive tests for database module.

Tests cover:
- Database connection management
- Singleton pattern behavior
- Repository CRUD operations
- Error handling
- Index creation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from bson import ObjectId
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from core.database.connection import Database, get_database, init_database
from core.database.repositories import UserRepository, ConversationRepository
from core.database.practice_repository import PracticeRepository
from core.models import UserProfile, Conversation, Message


class TestDatabaseConnection:
    """Test Database class and connection management."""

    def test_database_is_singleton(self):
        """Test that Database follows singleton pattern."""
        db1 = Database()
        db2 = Database()
        assert db1 is db2

    def test_get_database_returns_singleton(self):
        """Test get_database returns same instance."""
        db1 = get_database()
        db2 = get_database()
        assert db1 is db2

    @patch('core.database.connection.MongoClient')
    def test_connect_success(self, mock_client):
        """Test successful database connection."""
        mock_mongo = MagicMock()
        mock_client.return_value = mock_mongo
        
        db = Database()
        db._client = None  # Reset
        db.connect()
        
        assert mock_client.called
        mock_mongo.admin.command.assert_called_with('ping')

    @patch('core.database.connection.MongoClient')
    def test_connect_already_connected(self, mock_client):
        """Test connect when already connected does nothing."""
        db = Database()
        db._client = MagicMock()
        
        db.connect()
        
        # Should not create new client
        mock_client.assert_not_called()

    @patch('core.database.connection.MongoClient')
    def test_connect_failure(self, mock_client):
        """Test connection failure handling."""
        mock_client.side_effect = ConnectionFailure("Connection failed")
        
        db = Database()
        db._client = None
        
        with pytest.raises(ConnectionFailure):
            db.connect()

    def test_disconnect(self):
        """Test disconnect closes connection."""
        db = Database()
        mock_client = MagicMock()
        db._client = mock_client
        db._db = MagicMock()
        
        db.disconnect()
        
        mock_client.close.assert_called_once()
        assert db._client is None
        assert db._db is None

    def test_get_database_not_connected(self):
        """Test get_database raises error when not connected."""
        db = Database()
        db._db = None
        
        with pytest.raises(RuntimeError, match="Not connected"):
            db.get_database()

    @patch('core.database.connection.MongoClient')
    def test_ping_success(self, mock_client):
        """Test ping returns True when connected."""
        db = Database()
        db._client = MagicMock()
        
        assert db.ping() is True

    def test_ping_not_connected(self):
        """Test ping returns False when not connected."""
        db = Database()
        db._client = None
        
        assert db.ping() is False

    def test_context_manager(self):
        """Test database context manager."""
        db = Database()
        db.connect = MagicMock()
        db.disconnect = MagicMock()
        
        with db:
            pass
        
        db.connect.assert_called_once()
        db.disconnect.assert_called_once()


class TestUserRepository:
    """Test UserRepository CRUD operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        collection = MagicMock()
        db.get_users_collection.return_value = collection
        return db, collection

    @pytest.fixture
    def user_repo(self, mock_db):
        """Create UserRepository with mocked database."""
        db, _ = mock_db
        with patch('core.database.repositories.get_database', return_value=db):
            return UserRepository()

    def test_create_user_success(self, user_repo, mock_db):
        """Test successful user creation."""
        _, collection = mock_db
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        user = UserProfile(
            email="test@example.com",
            username="testuser",
            password_hash="hash123"
        )
        
        user_id = user_repo.create_user(user)
        
        assert isinstance(user_id, str)
        collection.insert_one.assert_called_once()

    def test_create_user_duplicate_email(self, user_repo, mock_db):
        """Test user creation with duplicate email."""
        _, collection = mock_db
        collection.insert_one.side_effect = DuplicateKeyError("Duplicate key")
        
        user = UserProfile(
            email="test@example.com",
            username="testuser",
            password_hash="hash123"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            user_repo.create_user(user)

    def test_get_user_by_email_found(self, user_repo, mock_db):
        """Test getting user by email when found."""
        _, collection = mock_db
        collection.find_one.return_value = {
            "_id": ObjectId(),
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash123"
        }
        
        user = user_repo.get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"

    def test_get_user_by_email_not_found(self, user_repo, mock_db):
        """Test getting user by email when not found."""
        _, collection = mock_db
        collection.find_one.return_value = None
        
        user = user_repo.get_user_by_email("notfound@example.com")
        
        assert user is None

    def test_update_user_success(self, user_repo, mock_db):
        """Test successful user update."""
        _, collection = mock_db
        collection.update_one.return_value = MagicMock(modified_count=1)
        
        # Use valid ObjectId format
        valid_id = str(ObjectId())
        result = user_repo.update_user(valid_id, {"username": "newname"})
        
        assert result is True

    def test_delete_user_success(self, user_repo, mock_db):
        """Test successful user deletion."""
        _, collection = mock_db
        collection.delete_one.return_value = MagicMock(deleted_count=1)
        
        # Use valid ObjectId format
        valid_id = str(ObjectId())
        result = user_repo.delete_user(valid_id)
        
        assert result is True


class TestConversationRepository:
    """Test ConversationRepository operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        conv_collection = MagicMock()
        msg_collection = MagicMock()
        db.get_conversations_collection.return_value = conv_collection
        db.get_messages_collection.return_value = msg_collection
        return db, conv_collection, msg_collection

    @pytest.fixture
    def conv_repo(self, mock_db):
        """Create ConversationRepository with mocked database."""
        db, _, _ = mock_db
        with patch('core.database.repositories.get_database', return_value=db):
            return ConversationRepository()

    def test_create_conversation_success(self, conv_repo, mock_db):
        """Test successful conversation creation."""
        _, conv_collection, _ = mock_db
        conv_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        conv_id = conv_repo.create_conversation(
            user_id="user123",
            title="Test Conversation"
        )
        
        assert isinstance(conv_id, str)
        conv_collection.insert_one.assert_called_once()

    def test_add_message_updates_conversation(self, conv_repo, mock_db):
        """Test that adding message updates conversation stats."""
        _, conv_collection, msg_collection = mock_db
        msg_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # Use valid ObjectId for conversation_id
        valid_conv_id = str(ObjectId())
        message = Message(
            conversation_id=valid_conv_id,
            user_id="user123",
            role="user",
            content="Test message"
        )
        
        msg_id = conv_repo.add_message(message)
        
        assert isinstance(msg_id, str)
        # Verify conversation was updated
        conv_collection.update_one.assert_called_once()

    def test_delete_conversation_deletes_messages(self, conv_repo, mock_db):
        """Test that deleting conversation also deletes its messages."""
        _, conv_collection, msg_collection = mock_db
        conv_collection.delete_one.return_value = MagicMock(deleted_count=1)
        
        # Use valid ObjectId format
        valid_id = str(ObjectId())
        result = conv_repo.delete_conversation(valid_id)
        
        assert result is True
        # Verify messages were deleted first
        msg_collection.delete_many.assert_called_once_with({"conversation_id": valid_id})
        conv_collection.delete_one.assert_called_once()


class TestPracticeRepository:
    """Test PracticeRepository operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        collection = MagicMock()
        # Mock the get_database method chain
        db.get_database.return_value = {"practice_sessions": collection}
        return db, collection

    @pytest.fixture
    def practice_repo(self, mock_db):
        """Create PracticeRepository with mocked database."""
        db, _ = mock_db
        return PracticeRepository(database=db)

    def test_save_session_success(self, practice_repo, mock_db):
        """Test successful session save."""
        _, collection = mock_db
        collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        session_data = {
            "topic": "Linear Algebra",
            "score": 8,
            "total_questions": 10,
            "completed_at": "2026-02-14T10:00:00"
        }
        
        result = practice_repo.save_session("user123", session_data)
        
        assert result is not None
        collection.insert_one.assert_called_once()


class TestDatabaseModule:
    """Test database module exports."""

    def test_exports_all_required_symbols(self):
        """Test that __all__ exports all required symbols."""
        from core.database import __all__
        
        expected = [
            "Database",
            "get_database",
            "init_database",
            "UserRepository",
            "ConversationRepository",
            "ProgressRepository",
            "PracticeRepository",
        ]
        assert set(__all__) == set(expected)

    def test_can_import_all_symbols(self):
        """Test that all exported symbols can be imported."""
        from core.database import (
            Database,
            get_database,
            init_database,
            UserRepository,
            ConversationRepository,
            ProgressRepository,
            PracticeRepository,
        )
        
        assert Database is not None
        assert callable(get_database)
        assert callable(init_database)
        assert UserRepository is not None
        assert ConversationRepository is not None
        assert ProgressRepository is not None
        assert PracticeRepository is not None
