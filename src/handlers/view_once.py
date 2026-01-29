"""
View-Once Handler
=================
Handles self-destructing (view-once) media.
MUST download first, then send as regular media.
"""

import os
import asyncio
from typing import Optional
from telethon.tl.types import Message

from .base import BaseHandler
from utils.media_utils import get_temp_path, cleanup_temp


class ViewOnceHandler(BaseHandler):
    """
    Handler for view-once (self-destructing) media.
    
    Flow:
        1. Detect view-once media
        2. Download immediately to temp folder
        3. Send as regular media via bot
        4. Delete temp file
    
    Note:
        Downloading view-once marks it as "seen" in the original chat.
    """
    
    VIEW_ONCE_CAPTION = "🔥 View-Once"
    
    def __init__(self, bot_manager, db, monitor_client):
        """
        Initialize view-once handler.
        
        Args:
            bot_manager: Bot manager instance
            db: Database operations instance
            monitor_client: Monitor's Telethon client for downloading
        """
        super().__init__(bot_manager, db)
        self.monitor = monitor_client
    
    async def handle(
        self,
        msg: Message,
        is_outgoing: bool,
        reply_to_group_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Handle view-once media.
        
        Args:
            msg: Telethon message with view-once media
            is_outgoing: True if you sent the message
            reply_to_group_id: Group message ID to reply to
            
        Returns:
            Optional[int]: Sent message ID in group
        """
        temp_path = None
        
        try:
            # Generate temp file path
            temp_path = get_temp_path(msg.id)
            
            self.logger.info(f"🔥 Downloading view-once media: {msg.id}")
            
            # Download media using monitor account
            downloaded_path = await self.monitor.download_media(
                message=msg,
                file=temp_path
            )
            
            if not downloaded_path or not os.path.exists(downloaded_path):
                self.logger.error("Failed to download view-once media")
                return None
            
            # Determine media type
            media_type = self._get_view_once_type(msg)
            
            # Build caption
            sender_name = self.bot_manager.get_sender_name(is_outgoing)
            caption = f"{self.VIEW_ONCE_CAPTION} from {sender_name}"
            
            # Send via appropriate bot
            group_msg_id = await self.bot_manager.send_file(
                file_path=downloaded_path,
                is_outgoing=is_outgoing,
                caption=caption,
                reply_to=reply_to_group_id
            )
            
            self.logger.info(f"✅ View-once {media_type} saved: {msg.id}")
            
            return group_msg_id
            
        except Exception as e:
            self.logger.error(f"Failed to handle view-once: {e}")
            return None
            
        finally:
            # Always cleanup temp file
            if temp_path:
                cleanup_temp(temp_path)
    
    def _get_view_once_type(self, msg: Message) -> str:
        """
        Determine view-once media type.
        
        Args:
            msg: Message with view-once media
            
        Returns:
            str: 'photo' or 'video'
        """
        if msg.photo:
            return "photo"
        elif msg.video:
            return "video"
        elif msg.document:
            # Check if it's a video document
            mime = getattr(msg.document, 'mime_type', '')
            if 'video' in mime:
                return "video"
            return "media"
        return "media"
    
    @staticmethod
    def is_view_once(msg: Message) -> bool:
        """
        Check if message contains view-once media.
        
        Args:
            msg: Telethon message object
            
        Returns:
            bool: True if view-once media
        """
        if not msg.media:
            return False
        
        # Check for TTL (time-to-live) attribute
        media = msg.media
        
        # Direct ttl_seconds check
        if hasattr(media, 'ttl_seconds') and media.ttl_seconds is not None:
            return True
        
        # Check photo
        if hasattr(media, 'photo') and media.photo:
            if hasattr(media, 'ttl_seconds') and media.ttl_seconds:
                return True
        
        # Check document
        if hasattr(media, 'document') and media.document:
            if hasattr(media, 'ttl_seconds') and media.ttl_seconds:
                return True
        
        return False


class ViewOnceRecovery:
    """
    Utility class to recover unopened view-once media
    when bot starts after being offline.
    """
    
    def __init__(self, handler: ViewOnceHandler):
        """
        Initialize recovery utility.
        
        Args:
            handler: ViewOnceHandler instance
        """
        self.handler = handler
        self.logger = handler.logger
    
    async def recover_unopened(
        self,
        chat_id: int,
        limit: int = 100
    ) -> int:
        """
        Scan recent messages for unopened view-once media.
        
        Args:
            chat_id: Chat ID to scan
            limit: Maximum messages to scan
            
        Returns:
            int: Number of recovered view-once media
        """
        recovered = 0
        
        try:
            async for msg in self.handler.monitor.iter_messages(
                chat_id,
                limit=limit
            ):
                # Check if view-once and not yet processed
                if ViewOnceHandler.is_view_once(msg):
                    exists = await self.handler.db.message_exists(msg.id)
                    
                    if not exists:
                        self.logger.info(f"🔍 Found unopened view-once: {msg.id}")
                        
                        result = await self.handler.handle(
                            msg=msg,
                            is_outgoing=msg.out
                        )
                        
                        if result:
                            recovered += 1
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
            
            return recovered
            
        except Exception as e:
            self.logger.error(f"View-once recovery failed: {e}")
            return recovered
