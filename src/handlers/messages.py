"""
Message Handler
===============
Handles text messages (no media).
"""

from typing import Optional
from telethon.tl.types import Message

from .base import BaseHandler


class MessageHandler(BaseHandler):
    """
    Handler for text-only messages.
    
    Responsibilities:
        - Forward text messages via appropriate bot
        - Maintain reply relationships
        - Handle formatted text (bold, italic, etc.)
    """
    
    async def handle(
        self,
        msg: Message,
        is_outgoing: bool,
        reply_to_group_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Handle text message.
        
        Args:
            msg: Telethon message object
            is_outgoing: True if you sent the message
            reply_to_group_id: Group message ID to reply to
            
        Returns:
            Optional[int]: Sent message ID in group
        """
        try:
            # Get message text
            text = msg.text
            
            if not text:
                self.logger.warning("Empty text message received")
                return None
            
            # Send via appropriate bot
            group_msg_id = await self.bot_manager.send_text(
                text=text,
                is_outgoing=is_outgoing,
                reply_to=reply_to_group_id
            )
            
            self.logger.debug(
                f"📝 Text sent: {text[:50]}{'...' if len(text) > 50 else ''}"
            )
            
            return group_msg_id
            
        except Exception as e:
            self.logger.error(f"Failed to handle text message: {e}")
            return None
    
    async def handle_with_entities(
        self,
        msg: Message,
        is_outgoing: bool,
        reply_to_group_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Handle text message preserving formatting entities.
        
        Args:
            msg: Telethon message object
            is_outgoing: True if you sent the message
            reply_to_group_id: Group message ID to reply to
            
        Returns:
            Optional[int]: Sent message ID in group
        """
        try:
            bot = self.bot_manager.get_bot(is_outgoing)
            
            # Send with entities preserved
            sent_msg = await bot.send_message(
                entity=self.bot_manager.group_id,
                message=msg.text,
                formatting_entities=msg.entities,
                reply_to=reply_to_group_id
            )
            
            return sent_msg.id
            
        except Exception as e:
            self.logger.error(f"Failed to handle formatted message: {e}")
            return None
