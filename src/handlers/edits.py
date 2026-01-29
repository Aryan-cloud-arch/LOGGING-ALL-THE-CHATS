"""
Edit Handler
============
Handles message edit detection and notification.
"""

from typing import Optional
from telethon.tl.types import Message

from .base import BaseHandler


class EditHandler(BaseHandler):
    """
    Handler for message edits.
    
    Flow:
        1. Detect edit event
        2. Find original message in database
        3. Send edit notification via bot
        4. Update edit history in database
    
    Note:
        Edit detection only works while bot is running.
        Cannot detect edits that occurred while offline.
    """
    
    EDIT_PREFIX = "✏️ Edited"
    
    async def handle(
        self,
        msg: Message,
        is_outgoing: bool
    ) -> Optional[int]:
        """
        Handle message edit.
        
        Args:
            msg: Edited message object
            is_outgoing: True if you edited the message
            
        Returns:
            Optional[int]: Edit notification message ID in group
        """
        try:
            # Find original message in database
            original = await self.db.get_message(msg.id)
            
            if not original:
                self.logger.warning(
                    f"Original message not found for edit: {msg.id}"
                )
                return None
            
            # Get the group message ID to reply to
            group_reply_id = original.get('group_id')
            
            if not group_reply_id:
                self.logger.warning("No group message ID for edit reference")
                return None
            
            # Build edit notification
            sender_name = self.bot_manager.get_sender_name(is_outgoing)
            edit_text = self._build_edit_message(msg, sender_name)
            
            # Send edit notification via bot
            group_msg_id = await self.bot_manager.send_text(
                text=edit_text,
                is_outgoing=is_outgoing,
                reply_to=group_reply_id
            )
            
            # Update edit history in database
            await self.db.add_edit(
                original_id=msg.id,
                new_content=msg.text,
                edit_notification_id=group_msg_id
            )
            
            self.logger.debug(f"✏️ Edit notification sent for: {msg.id}")
            
            return group_msg_id
            
        except Exception as e:
            self.logger.error(f"Failed to handle edit: {e}")
            return None
    
    def _build_edit_message(self, msg: Message, sender_name: str) -> str:
        """
        Build edit notification message.
        
        Args:
            msg: Edited message
            sender_name: Name of who edited
            
        Returns:
            str: Formatted edit notification
        """
        new_text = msg.text or "[Media caption edited]"
        
        return f"{self.EDIT_PREFIX}:\n\n{new_text}"
    
    async def compare_offline_edits(
        self,
        chat_id: int,
        limit: int = 100
    ) -> int:
        """
        Compare recent messages with stored versions
        to detect edits that occurred while offline.
        
        Args:
            chat_id: Chat ID to scan
            limit: Maximum messages to check
            
        Returns:
            int: Number of edits detected
        """
        edits_found = 0
        
        try:
            async for msg in self.bot_manager.your_bot.iter_messages(
                chat_id,
                limit=limit
            ):
                # Get stored version
                stored = await self.db.get_message(msg.id)
                
                if not stored:
                    continue
                
                # Compare content
                stored_content = stored.get('content', '')
                current_content = msg.text or ''
                
                if stored_content != current_content:
                    self.logger.info(f"🔍 Offline edit detected: {msg.id}")
                    
                    # Process as edit
                    await self.handle(msg, msg.out)
                    edits_found += 1
            
            return edits_found
            
        except Exception as e:
            self.logger.error(f"Offline edit comparison failed: {e}")
            return edits_found
