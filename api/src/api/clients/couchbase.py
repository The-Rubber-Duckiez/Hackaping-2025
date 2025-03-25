import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions, QueryOptions
from couchbase.auth import PasswordAuthenticator

from ..utils import log

logger = log.get_logger(__name__)

class CouchbaseChatClient:
    def __init__(
        self,
        url: str = None,
        username: str = None,
        password: str = None,
        bucket_name: str = None,
        scope: str = "_default",
        chats_coll: str = "chats",
        messages_coll: str = "chat_messages"
    ):
        self.url = url
        self.username = username
        self.password = password
        self.bucket_name = bucket_name
        self.scope_name = scope
        self.chats_coll = chats_coll
        self.messages_coll = messages_coll
        self.cluster = None
        self.bucket = None
        self.scope = None
        self.chats = None
        self.messages = None

    def connect(self) -> None:
        """Establish connection to Couchbase database."""
        auth = PasswordAuthenticator(self.username, self.password)
        options = ClusterOptions(auth)

        self.cluster = Cluster(self.url, options)

        try:
            self.bucket = self.cluster.bucket(self.bucket_name)
            self.scope = self.bucket.scope(self.scope_name)
            try:
                self.init()
            except Exception as col_err:
                logger.warning(f"Collections not ready yet: {str(col_err)}")

            logger.info("Connected to Couchbase database with bucket")
        except Exception as bucket_err:
            logger.warning(f"Bucket not ready yet: {str(bucket_err)}")

    def init(self) -> None:
        """Create the collections if they don't exist."""
        if not self.cluster:
            self.connect()

        try:
            bucket = self.cluster.bucket(self.bucket_name)
            collection_manager = bucket.collections()

            for coll in [self.messages_coll, self.chats_coll]:
                try:
                    collection_manager.create_collection(self.scope_name, coll)
                    logger.info(f"Created collection: {self.chats_coll}")
                except Exception as e:
                    if "already exists" in str(e):
                        pass
                    else:
                        logger.warning(
                            f"Error creating collection {self.chats_coll}: {str(e)}"
                        )

            self.chats = self.scope.collection(self.chats_coll)
            self.messages = self.scope.collection(self.messages_coll)

            logger.info("Collections initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing collections: {str(e)}")
            raise

    def create_chat(self, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new chat session.

        Args:
            metadata: Optional metadata for the chat session

        Returns:
            The UUID of the created chat session
        """
        if not self.chats:
            self.init()

        chat_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        doc = {
            "id": chat_id,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {}
        }

        try:
            self.chats.upsert(chat_id, doc)
            logger.info(f"Created chat session with ID: {chat_id}")
            return chat_id
        except Exception:
            logger.exception("Failed to create chat")
            raise

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """
        Add a message to an existing chat session.

        Args:
            chat_id: The UUID of the chat session
            role: The role of the message sender (e.g., 'user', 'assistant')
            content: The content of the message
            metadata: Optional metadata for the message

        Returns:
            The ID of the added message
        """
        if not self.messages:
            self.init()

        try:
            chat = self.get_chat(chat_id)
            if not chat:
                raise ValueError(f"Chat with ID {chat_id} not found")

            # Update chat's timestamp
            chat["updated_at"] = datetime.utcnow().isoformat()
            self.chats.upsert(chat_id, chat)

            # NOTE: Message ID is just a timestamp, for sortability
            message_id = int(datetime.utcnow().timestamp() * 1000)

            message_key = f"{chat_id}:{message_id}"
            message_doc = {
                "id": message_id,
                "chat_id": chat_id,
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            self.messages.upsert(message_key, message_doc)

            logger.info(f"Added message with ID {message_id} to chat {chat_id}")
            return message_id
        except Exception:
            logger.exception("Failed to add message.")
            raise

    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chat session by ID.

        Args:
            chat_id: The UUID of the chat session

        Returns:
            The chat session details or None if not found
        """
        if not self.chats:
            self.init()

        try:
            result = self.chats.get(chat_id)

            if not result or not hasattr(result, 'value') or not result.value:
                return None

            return result.value
        except Exception as e:
            logger.warning(f"Failed to get chat: {str(e)}")
            return None

    def get_messages(self, chat_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a chat session.

        Args:
            chat_id: The UUID of the chat session

        Returns:
            List of messages in the chat session
        """
        if not self.messages:
            self.init()

        try:
            query = f"""
            SELECT m.*
            FROM {self.bucket_name}.{self.scope_name}.{self.messages_coll} m
            WHERE m.chat_id = $chat_id
            ORDER BY m.created_at ASC
            """

            options = QueryOptions(named_parameters={"chat_id": chat_id})
            result = self.cluster.query(query, options)
            return [row for row in result]
        except Exception:
            logger.exception("Failed to get messages.")
            raise

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat session and all its messages.

        Args:
            chat_id: The UUID of the chat session

        Returns:
            True if the chat was deleted, False otherwise
        """
        if not self.chats or not self.messages:
            self.init()

        try:
            chat = self.get_chat(chat_id)
            if not chat:
                return False

            # Delete messages
            query = f"""
            DELETE FROM {self.bucket_name}.{self.scope_name}.{self.messages_coll} m
            WHERE m.chat_id = $chat_id
            """

            options = QueryOptions(named_parameters={"chat_id": chat_id})
            self.cluster.query(query, options)
            logger.info(f"Deleted messages for chat {chat_id}")

            # Delete the chat
            self.chats.remove(chat_id)
            logger.info(f"Deleted chat {chat_id}")
            return True
        except Exception:
            logger.error("Failed to delete chat.")
            raise

    def close(self) -> None:
        """Close the database connection."""
        if self.cluster:
            self.cluster = None
            logger.info("Database connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
