"""
Media Handler
=============
Handles all media types (photos, videos, documents, etc.)
Uses direct forwarding - NO download required!
"""

from typing import Optional
from telethon.tl.types import (
    Message,
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaContact,
    MessageMediaGeo,
    MessageMediaPoll
)

from .base import BaseHandler


class MediaHandler(BaseHandler):
    """
    Handler for media messages.
    
    Supported media types:
        - Photos
        - Videos
        - Documents/Files
        - Voice messages
        - Video notes (round videos)
        - Stickers
        - GIFs
        - Contacts
        - Locations
        - Polls
    
    Note:
        Uses direct forwarding via bot - no download needed!
        This bypasses the 50MB HTTP API limit.
    """
    
    def __init__(self, bot_manager, db, monitor_client):
        """
        Initialize media handler.
        
        Args:
            bot_manager: Bot manager instance
            db: Database operations instance
            monitor_client: Monitor's Telethon client
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
        Handle media message by forwarding via bot.
        
        Args:
            msg: Telethon message object with media
            is_outgoing: True if you sent the message
            reply_to_group_id: Group message ID to reply to
            
        Returns:
            Optional[int]: Sent message ID in group
        """
        try:
            # Get media type for logging
            media_type = self._get_media_type(msg.media)
            
            # Get caption if any
            caption = msg.text or ""
            
            # Send media via appropriate bot
            group_msg_id = await self.bot_manager.send_media(
                media=msg.media,
                is_outgoing=is_outgoing,
                caption=caption,
                reply_to=reply_to_group_id
            )
            
            self.logger.debug(f"📎 {media_type} sent successfully")
            
            return group_msg_id
            
        except Exception as e:
            self.logger.error(f"Failed to handle media: {e}")
            
            # Fallback: try direct forward
            return await self._fallback_forward(msg, is_outgoing)
    
    async def _fallback_forward(
        self,
        msg: Message,
        is_outgoing: bool
    ) -> Optional[int]:
        """
        Fallback method: Forward directly using monitor account.
        Used when bot forwarding fails.
        
        Args:
            msg: Original message
            is_outgoing: True if you sent the message
            
        Returns:
            Optional[int]: Forwarded message ID in group
        """
        try:
            self.logger.warning("Using fallback forward method")
            
            # Forward using monitor account
            forwarded = await self.monitor.forward_messages(
                entity=self.bot_manager.group_id,
                messages=msg
            )
            
            # Add context via bot
            bot = self.bot_manager.get_bot(is_outgoing)
            sender_name = self.bot_manager.get_sender_name(is_outgoing)
            
            await bot.send_message(
                entity=self.bot_manager.group_id,
                message=f"👤 {sender_name} (forwarded directly)",
                reply_to=forwarded.id
            )
            
            return forwarded.id
            
        except Exception as e:
            self.logger.error(f"Fallback forward failed: {e}")
            return None
    
    def _get_media_type(self, media) -> str:
        """
        Get human-readable media type.
        
        Args:
            media: Telethon media object
            
        Returns:
            str: Media type description
        """
        if isinstance(media, MessageMediaPhoto):
            return "Photo"
        
        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            
            if doc is None:
                return "Document"
            
            # Check attributes for specific types
            for attr in doc.attributes:
                attr_name = type(attr).__name__
                
                if 'Video' in attr_name:
                    if 'Round' in attr_name:
                        return "Video Note"
                    return "Video"
                
                elif 'Audio' in attr_name:
                    if hasattr(attr, 'voice') and attr.voice:
                        return "Voice Message"
                    return "Audio"
                
                elif 'Sticker' in attr_name:
                    return "Sticker"
                
                elif 'Animated' in attr_name:
                    return "GIF"
            
            return "Document"
        
        elif isinstance(media, MessageMediaContact):
            return "Contact"
        
        elif isinstance(media, MessageMediaGeo):
            return "Location"
        
        elif isinstance(media, MessageMediaPoll):
            return "Poll"
        
        else:
            return "Unknown Media"
    
    async def handle_album(
        self,
        messages: list,
        is_outgoing: bool
    ) -> Optional[list]:
        """
        Handle media album (multiple photos/videos in one message).
        
        Args:
            messages: List of grouped messages
            is_outgoing: True if you sent the album
            
        Returns:
            Optional[list]: List of sent message IDs in group
        """
        try:
            bot = self.bot_manager.get_bot(is_outgoing)
            
            # Collect all media from the album
            media_list = [msg.media for msg in messages if msg.media]
            
            # Get caption from first message
            caption = messages[0].text or ""
            
            # Send as album
            sent_messages = await bot.send_file(
                entity=self.bot_manager.group_id,
                file=media_list,
                caption=caption
            )
            
            self.logger.debug(f"📸 Album with {len(media_list)} items sent")
            
            # Return list of message IDs
            if isinstance(sent_messages, list):
                return [msg.id for msg in sent_messages]
            return [sent_messages.id]
            
        except Exception as e:
            self.logger.error(f"Failed to handle album: {e}")
            return None
