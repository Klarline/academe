"""Repository classes for database operations in Academe."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, OperationFailure

from core.utils import get_current_time

from core.models import (
    Conversation,
    ConversationSummary,
    Message,
    UserProfile,
)

from .connection import get_database

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self):
        """Initialize user repository."""
        self.db = get_database()

    def create_user(self, user: UserProfile) -> str:
        """
        Create a new user in the database.

        Args:
            user: UserProfile object

        Returns:
            User ID as string

        Raises:
            ValueError: If user with email already exists
        """
        try:
            collection = self.db.get_users_collection()
            user_dict = user.to_mongo_dict()

            # Remove id if it's None
            if '_id' in user_dict and user_dict['_id'] is None:
                del user_dict['_id']

            result = collection.insert_one(user_dict)
            logger.info(f"Created user with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except DuplicateKeyError:
            logger.error(f"User with email {user.email} already exists")
            raise ValueError(f"User with email {user.email} already exists")
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise

    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            UserProfile if found, None otherwise
        """
        try:
            collection = self.db.get_users_collection()
            user_dict = collection.find_one({"email": email.lower()})

            if user_dict:
                return UserProfile.from_mongo_dict(user_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            raise

    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            UserProfile if found, None otherwise
        """
        try:
            collection = self.db.get_users_collection()
            user_dict = collection.find_one({"_id": ObjectId(user_id)})

            if user_dict:
                return UserProfile.from_mongo_dict(user_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            raise

    def get_user_by_username(self, username: str) -> Optional[UserProfile]:
        """
        Get user by username.

        Args:
            username: User's username

        Returns:
            UserProfile if found, None otherwise
        """
        try:
            collection = self.db.get_users_collection()
            user_dict = collection.find_one({"username": username.lower()})

            if user_dict:
                return UserProfile.from_mongo_dict(user_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to get user by username: {e}")
            raise

    def update_user(self, user_id: str, updates: Dict) -> bool:
        """
        Update user information.

        Args:
            user_id: User's ID
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            collection = self.db.get_users_collection()

            # Add updated_at timestamp
            updates["updated_at"] = get_current_time()

            # Remove _id from updates if present
            updates.pop("_id", None)
            updates.pop("id", None)

            result = collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": updates}
            )

            if result.modified_count > 0:
                logger.info(f"Updated user {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise

    def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User's ID

        Returns:
            True if updated successfully
        """
        return self.update_user(user_id, {"last_login_at": get_current_time()})

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user from the database.

        Args:
            user_id: User's ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            collection = self.db.get_users_collection()
            result = collection.delete_one({"_id": ObjectId(user_id)})

            if result.deleted_count > 0:
                logger.info(f"Deleted user {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            raise

    def count_users(self) -> int:
        """
        Get total number of users.

        Returns:
            Number of users
        """
        try:
            collection = self.db.get_users_collection()
            return collection.count_documents({})
        except Exception as e:
            logger.error(f"Failed to count users: {e}")
            raise


class ConversationRepository:
    """Repository for conversation-related database operations."""

    def __init__(self):
        """Initialize conversation repository."""
        self.db = get_database()

    def create_conversation(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None
    ) -> str:
        """
        Create a new conversation.

        Args:
            user_id: User's ID
            title: Conversation title
            description: Optional description

        Returns:
            Conversation ID as string
        """
        try:
            collection = self.db.get_conversations_collection()

            conversation = Conversation(
                user_id=user_id,
                title=title,
                description=description
            )

            conv_dict = conversation.to_mongo_dict()
            if '_id' in conv_dict and conv_dict['_id'] is None:
                del conv_dict['_id']

            result = collection.insert_one(conv_dict)
            logger.info(f"Created conversation with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation if found, None otherwise
        """
        try:
            collection = self.db.get_conversations_collection()
            conv_dict = collection.find_one({"_id": ObjectId(conversation_id)})

            if conv_dict:
                return Conversation.from_mongo_dict(conv_dict)
            return None

        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            raise

    def get_user_conversations(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50
    ) -> List[ConversationSummary]:
        """
        Get user's conversations.

        Args:
            user_id: User's ID
            include_archived: Whether to include archived conversations
            limit: Maximum number of conversations to return

        Returns:
            List of conversation summaries
        """
        try:
            collection = self.db.get_conversations_collection()

            query = {"user_id": user_id}
            if not include_archived:
                query["is_archived"] = False

            cursor = collection.find(query).sort("updated_at", -1).limit(limit)

            conversations = []
            for conv_dict in cursor:
                conversation = Conversation.from_mongo_dict(conv_dict)
                conversations.append(ConversationSummary.from_conversation(conversation))

            return conversations

        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}")
            raise

    def update_conversation(self, conversation_id: str, updates: Dict) -> bool:
        """
        Update conversation information.

        Args:
            conversation_id: Conversation ID
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully
        """
        try:
            collection = self.db.get_conversations_collection()

            # Add updated_at timestamp
            updates["updated_at"] = get_current_time()

            # Remove _id from updates if present
            updates.pop("_id", None)
            updates.pop("id", None)

            result = collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": updates}
            )

            if result.modified_count > 0:
                logger.info(f"Updated conversation {conversation_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to update conversation: {e}")
            raise

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted successfully
        """
        try:
            # Delete all messages first
            messages_collection = self.db.get_messages_collection()
            messages_collection.delete_many({"conversation_id": conversation_id})

            # Delete conversation
            conv_collection = self.db.get_conversations_collection()
            result = conv_collection.delete_one({"_id": ObjectId(conversation_id)})

            if result.deleted_count > 0:
                logger.info(f"Deleted conversation {conversation_id} and its messages")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            raise

    def add_message(self, message: Message) -> str:
        """
        Add a message to a conversation.

        Args:
            message: Message object

        Returns:
            Message ID as string
        """
        try:
            # Insert message
            messages_collection = self.db.get_messages_collection()
            message_dict = message.to_mongo_dict()

            if '_id' in message_dict and message_dict['_id'] is None:
                del message_dict['_id']

            result = messages_collection.insert_one(message_dict)
            message_id = str(result.inserted_id)

            # Update conversation stats
            conv_collection = self.db.get_conversations_collection()
            conv_collection.update_one(
                {"_id": ObjectId(message.conversation_id)},
                {
                    "$inc": {"message_count": 1},
                    "$set": {
                        "last_message_at": message.timestamp,
                        "updated_at": get_current_time()
                    }
                }
            )

            logger.info(f"Added message {message_id} to conversation {message.conversation_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise

    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of messages ordered by timestamp
        """
        try:
            collection = self.db.get_messages_collection()

            query = {"conversation_id": conversation_id}
            cursor = collection.find(query).sort("timestamp", 1)

            if limit:
                cursor = cursor.limit(limit)

            messages = []
            for msg_dict in cursor:
                messages.append(Message.from_mongo_dict(msg_dict))

            return messages

        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            raise

    def get_recent_messages(
        self,
        conversation_id: str,
        count: int = 10
    ) -> List[Message]:
        """
        Get most recent messages from a conversation.

        Args:
            conversation_id: Conversation ID
            count: Number of messages to retrieve

        Returns:
            List of recent messages
        """
        try:
            collection = self.db.get_messages_collection()

            cursor = collection.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", -1).limit(count)

            messages = []
            for msg_dict in cursor:
                messages.append(Message.from_mongo_dict(msg_dict))

            # Reverse to get chronological order
            return list(reversed(messages))

        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            raise

    def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[ConversationSummary]:
        """
        Search user's conversations by title or content.

        Args:
            user_id: User's ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching conversation summaries
        """
        try:
            collection = self.db.get_conversations_collection()

            # Simple text search on title
            cursor = collection.find({
                "user_id": user_id,
                "title": {"$regex": query, "$options": "i"}
            }).limit(limit)

            conversations = []
            for conv_dict in cursor:
                conversation = Conversation.from_mongo_dict(conv_dict)
                conversations.append(ConversationSummary.from_conversation(conversation))

            return conversations

        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            raise