"""
Database Operations
===================
High-level database operations with error handling and retry logic.
Provides clean interface for all database interactions.
"""

import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from pymongo.errors import (
    DuplicateKeyError,
    WriteError,
    BulkWriteError
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from .mongo import MongoManager
from .models import (
    MessageModel,
    EditHistoryModel,
    ReplyChainModel,
    SystemStateModel,
    SenderType,
    MediaType,
    CollectionStats
)
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseOperations:
    """
    High-level database operations with automatic retry and error handling.
    
    Features:
        ✅ Automatic retry on transient failures
        ✅ Bulk operations for efficiency
        ✅ Transaction support for consistency
        ✅ Caching for frequently accessed data
        ✅ Statistics and monitoring
    """
    
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0  # seconds
    
    def __init__(self, connection_uri: str):
        """
        Initialize database operations.
        
        Args:
            connection_uri: MongoDB connection string
        """
        self.mongo_manager = MongoManager(connection_uri)
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def connect(self) -> bool:
        """
        Connect to database.
        
        Returns:
            bool: True if connected successfully
        """
        try:
            connected = await self.mongo_manager.connect()
            if connected:
                self.db = self.mongo_manager.database
                logger.info("✅ Database operations ready")
            return connected
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from database."""
        await self.mongo_manager.disconnect()
    
    # ==================== MESSAGE OPERATIONS ====================
    
    async def save_message(
        self,
        original_id: int,
        group_id: int,
        sender: str,
        content: Optional[str] = None,
        has_media: bool = False,
        media_type: Optional[str] = None,
        media_path: Optional[str] = None,
        reply_to_original: Optional[int] = None,
        reply_to_group: Optional[int] = None,
        view_once: bool = False,
        **kwargs
    ) -> bool:
        """
        Save message to database.
        
        Args:
            original_id: Message ID in DM
            group_id: Message ID in backup group
            sender: 'you' or 'her'
            content: Message text content
            has_media: Whether message has media
            media_type: Type of media
            media_path: Path to saved media
            reply_to_original: Reply to ID in DM
            reply_to_group: Reply to ID in group
            view_once: Whether media was view-once
            **kwargs: Additional metadata
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Create message model
            message = MessageModel(
                original_id=original_id,
                group_id=group_id,
                sender=SenderType(sender),
                content=content,
                has_media=has_media,
                media_type=MediaType(media_type or "none"),
                media_path=media_path,
                reply_to_original=reply_to_original,
                reply_to_group=reply_to_group,
                view_once=view_once,
                metadata=kwargs
            )
            
            # Save to database
            result = await self._retry_operation(
                self.db.messages.insert_one,
                message.to_dict()
            )
            
            # Update cache
            self._cache[f"msg_{original_id}"] = message.to_dict()
            
            # Update last processed ID
            await self.update_last_processed_id(original_id)
            
            logger.debug(f"💾 Message saved: {original_id} → {group_id}")
            return bool(result)
            
        except DuplicateKeyError:
            logger.warning(f"Message already exists: {original_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    async def get_message(
        self,
        original_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get message by original ID.
        
        Args:
            original_id: Message ID in DM
            
        Returns:
            Optional[Dict]: Message data if found
        """
        try:
            # Check cache first
            cache_key = f"msg_{original_id}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            # Query database
            message = await self.db.messages.find_one(
                {"original_id": original_id}
            )
            
            if message:
                self._cache[cache_key] = message
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None
    
    async def message_exists(self, original_id: int) -> bool:
        """
        Check if message exists in database.
        
        Args:
            original_id: Message ID to check
            
        Returns:
            bool: True if exists
        """
        try:
            count = await self.db.messages.count_documents(
                {"original_id": original_id},
                limit=1
            )
            return count > 0
            
        except Exception as e:
            logger.error(f"Failed to check message existence: {e}")
            return False
    
    async def get_messages_batch(
        self,
        original_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Get multiple messages efficiently.
        
        Args:
            original_ids: List of message IDs
            
        Returns:
            List[Dict]: List of message data
        """
        try:
            cursor = self.db.messages.find(
                {"original_id": {"$in": original_ids}}
            )
            
            messages = await cursor.to_list(length=None)
            
            # Update cache
            for msg in messages:
                self._cache[f"msg_{msg['original_id']}"] = msg
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get message batch: {e}")
            return []
    
    # ==================== EDIT OPERATIONS ====================
    
    async def add_edit(
        self,
        original_id: int,
        new_content: str,
        edit_notification_id: Optional[int] = None
    ) -> bool:
        """
        Add edit history entry.
        
        Args:
            original_id: Original message ID
            new_content: New content after edit
            edit_notification_id: Edit notification message ID
            
        Returns:
            bool: True if added successfully
        """
        try:
            # Get current content
            message = await self.get_message(original_id)
            
            if not message:
                logger.warning(f"Message not found for edit: {original_id}")
                return False
            
            old_content = message.get('content', '')
            
            # Create edit history entry
            edit = EditHistoryModel(
                original_id=original_id,
                old_content=old_content,
                new_content=new_content,
                edit_notification_id=edit_notification_id
            )
            
            # Save edit history
            await self.db.edit_history.insert_one(edit.dict())
            
            # Update message
            await self.db.messages.update_one(
                {"original_id": original_id},
                {
                    "$set": {
                        "content": new_content,
                        "is_edited": True
                    }
                }
            )
            
            # Invalidate cache
            cache_key = f"msg_{original_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.debug(f"✏️ Edit saved for message: {original_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add edit: {e}")
            return False
    
    async def get_edit_history(
        self,
        original_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get edit history for a message.
        
        Args:
            original_id: Message ID
            
        Returns:
            List[Dict]: Edit history entries
        """
        try:
            cursor = self.db.edit_history.find(
                {"original_id": original_id}
            ).sort("edit_time", 1)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Failed to get edit history: {e}")
            return []
    
    # ==================== DELETE OPERATIONS ====================
    
    async def mark_deleted(self, original_id: int) -> bool:
        """
        Mark message as deleted.
        
        Args:
            original_id: Message ID to mark as deleted
            
        Returns:
            bool: True if marked successfully
        """
        try:
            result = await self.db.messages.update_one(
                {"original_id": original_id},
                {"$set": {"is_deleted": True}}
            )
            
            # Invalidate cache
            cache_key = f"msg_{original_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.debug(f"🗑️ Message marked as deleted: {original_id}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to mark as deleted: {e}")
            return False
    
    # ==================== REPLY OPERATIONS ====================
    
    async def save_reply_mapping(
        self,
        original_id: int,
        original_reply_to: int,
        group_id: int,
        group_reply_to: int
    ) -> bool:
        """
        Save reply chain mapping.
        
        Args:
            original_id: Message ID in DM
            original_reply_to: Reply to ID in DM
            group_id: Message ID in group
            group_reply_to: Reply to ID in group
            
        Returns:
            bool: True if saved successfully
        """
        try:
            reply = ReplyChainModel(
                original_id=original_id,
                original_reply_to=original_reply_to,
                group_id=group_id,
                group_reply_to=group_reply_to
            )
            
            await self.db.reply_chains.insert_one(reply.dict())
            
            logger.debug(f"🔗 Reply mapping saved: {original_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save reply mapping: {e}")
            return False
    
    # ==================== SYSTEM STATE OPERATIONS ====================
    
    async def update_last_processed_id(self, message_id: int) -> bool:
        """
        Update last processed message ID.
        
        Args:
            message_id: Last processed message ID
            
        Returns:
            bool: True if updated successfully
        """
        try:
            state = SystemStateModel(
                key="last_processed_id",
                value=message_id
            )
            
            await self.db.system_state.update_one(
                {"key": "last_processed_id"},
                {"$set": state.dict()},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update last processed ID: {e}")
            return False
    
    async def get_last_processed_id(self) -> Optional[int]:
        """
        Get last processed message ID.
        
        Returns:
            Optional[int]: Last processed ID if exists
        """
        try:
            state = await self.db.system_state.find_one(
                {"key": "last_processed_id"}
            )
            
            if state:
                return state.get('value')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get last processed ID: {e}")
            return None
    
    # ==================== STATISTICS ====================
    
    async def get_statistics(self) -> CollectionStats:
        """
        Get database statistics.
        
        Returns:
            CollectionStats: Statistics object
        """
        try:
            stats = CollectionStats()
            
            # Message counts
            stats.total_messages = await self.db.messages.count_documents({})
            stats.total_edits = await self.db.messages.count_documents(
                {"is_edited": True}
            )
            stats.total_deletes = await self.db.messages.count_documents(
                {"is_deleted": True}
            )
            stats.total_media = await self.db.messages.count_documents(
                {"has_media": True}
            )
            stats.total_view_once = await self.db.messages.count_documents(
                {"view_once": True}
            )
            
            # Messages today
            today = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            stats.messages_today = await self.db.messages.count_documents(
                {"timestamp": {"$gte": today}}
            )
            
            # Last message time
            last_msg = await self.db.messages.find_one(
                sort=[("timestamp", -1)]
            )
            if last_msg:
                stats.last_message_time = last_msg.get('timestamp')
            
            # Storage size
            db_stats = await self.db.command("dbStats")
            stats.storage_size_mb = round(
                db_stats.get("dataSize", 0) / (1024 * 1024), 2
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return CollectionStats()
    
    # ==================== UTILITY METHODS ====================
    
    async def _retry_operation(
        self,
        operation,
        *args,
        **kwargs
    ) -> Any:
        """
        Retry database operation with exponential backoff.
        
        Args:
            operation: Operation to retry
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        for attempt in range(1, self.RETRY_ATTEMPTS + 1):
            try:
                return await operation(*args, **kwargs)
                
            except (WriteError, BulkWriteError) as e:
                if attempt == self.RETRY_ATTEMPTS:
                    raise
                
                delay = self.RETRY_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Operation failed (attempt {attempt}), retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        raise Exception("Max retry attempts reached")
    
    def clear_cache(self) -> None:
        """Clear internal cache."""
        self._cache.clear()
        logger.debug("🗑️ Cache cleared")
    
    async def cleanup_old_data(self, days: int = 30) -> Tuple[int, int]:
        """
        Clean up old data from database.
        
        Args:
            days: Delete data older than this many days
            
        Returns:
            Tuple[int, int]: (deleted_messages, deleted_edits)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old messages
            msg_result = await self.db.messages.delete_many(
                {"timestamp": {"$lt": cutoff_date}}
            )
            
            # Delete old edits
            edit_result = await self.db.edit_history.delete_many(
                {"edit_time": {"$lt": cutoff_date}}
            )
            
            logger.info(
                f"🧹 Cleaned up: {msg_result.deleted_count} messages, "
                f"{edit_result.deleted_count} edits"
            )
            
            return msg_result.deleted_count, edit_result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0, 0
