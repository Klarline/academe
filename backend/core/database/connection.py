"""MongoDB connection management for Academe."""

import logging
import threading
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase
from pymongo.errors import ConnectionFailure, OperationFailure

from core.config.settings import get_settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB connection manager with thread-safe singleton pattern."""

    _instance: Optional["Database"] = None
    _client: Optional[MongoClient] = None
    _db: Optional[MongoDatabase] = None
    _lock = threading.Lock()

    def __new__(cls) -> "Database":
        """Implement thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database connection parameters."""
        if self._client is None:
            self.settings = get_settings()
            self.mongodb_uri = self.settings.mongodb_uri
            self.db_name = self.settings.mongodb_db_name

    def connect(self) -> None:
        """
        Establish connection to MongoDB.

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        if self._client is not None:
            logger.debug("Already connected to MongoDB")
            return

        try:
            logger.info(f"Connecting to MongoDB at {self.mongodb_uri}")

            # Create client with connection pooling
            self._client = MongoClient(
                self.mongodb_uri,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
            )

            # Test connection
            self._client.admin.command('ping')

            # Get database
            self._db = self._client[self.db_name]

            logger.info(f"Successfully connected to MongoDB database: {self.db_name}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._client = None
            self._db = None
            raise ConnectionFailure(f"Cannot connect to MongoDB: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self._client = None
            self._db = None
            raise

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            logger.info("Closing MongoDB connection")
            self._client.close()
            self._client = None
            self._db = None

    def get_database(self) -> MongoDatabase:
        """
        Get database instance.

        Returns:
            MongoDB database instance

        Raises:
            RuntimeError: If not connected to database
        """
        if self._db is None:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self._db

    def get_users_collection(self) -> Collection:
        """
        Get users collection.

        Returns:
            Users collection
        """
        return self.get_database()["users"]

    def get_conversations_collection(self) -> Collection:
        """
        Get conversations collection.

        Returns:
            Conversations collection
        """
        return self.get_database()["conversations"]

    def get_messages_collection(self) -> Collection:
        """
        Get messages collection.

        Returns:
            Messages collection
        """
        return self.get_database()["messages"]

    def ping(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connected and responsive, False otherwise
        """
        try:
            if self._client:
                self._client.admin.command('ping')
                return True
        except (ConnectionFailure, OperationFailure):
            pass
        return False

    def get_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with database stats
        """
        if not self._db:
            return {"connected": False}

        try:
            stats = self._db.command("dbStats")
            return {
                "connected": True,
                "database": self.db_name,
                "collections": stats.get("collections", 0),
                "documents": stats.get("objects", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"connected": False, "error": str(e)}

    def create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # Users collection indexes
            users = self.get_users_collection()
            users.create_index([("email", 1)], unique=True)
            users.create_index([("username", 1)])
            users.create_index([("created_at", -1)])

            # Conversations collection indexes
            conversations = self.get_conversations_collection()
            conversations.create_index([("user_id", 1)])
            conversations.create_index([("created_at", -1)])
            conversations.create_index([("updated_at", -1)])
            conversations.create_index([("is_archived", 1)])

            # Messages collection indexes
            messages = self.get_messages_collection()
            messages.create_index([("conversation_id", 1)])
            messages.create_index([("user_id", 1)])
            messages.create_index([("timestamp", -1)])
            messages.create_index([("conversation_id", 1), ("timestamp", 1)])

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise

    def drop_database(self) -> None:
        """
        Drop the entire database. USE WITH CAUTION!

        This is mainly for testing purposes.
        """
        if self._client and self._db:
            logger.warning(f"Dropping database: {self.db_name}")
            self._client.drop_database(self.db_name)
            self._db = self._client[self.db_name]

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._client else "disconnected"
        return f"<Database({self.db_name}) {status}>"


# Global database instance
db = Database()


def get_database() -> Database:
    """
    Get global database instance.

    Returns:
        Database instance
    """
    return db


def init_database() -> None:
    """Initialize database connection and create indexes."""
    database = get_database()
    database.connect()
    database.create_indexes()
    logger.info("Database initialized successfully")