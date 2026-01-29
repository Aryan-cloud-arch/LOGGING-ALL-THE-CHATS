"""
Delete Handler
==============
Handles message deletion detection and notification.
"""

from typing import Optional

from .base import BaseHandler


class DeleteHandler(BaseHandler):
    """
    Handler for message deletions.
    
    Flow:
        1. Detect delete event
        2. Find original message in database
        3. Send delete notification via bot
        4. Mark as deleted in database
    
    Note:
        Original message content is preserved in group!
        Only a notification is added.
    """
    
    DELETE_PREFIX = "🗑️ Deleted"
    
    async def handle(self, original_msg_id: int) -> Optional[int]:
        """
        Handle message deletion.
        
        Args:
            original_msg_id: ID of deleted message
            
        Returns:
            Optional[int]: Delete notification message ID in group
        """
        try:
            # Find original message in database
            original = await self.db.get_message(original_msg_id)
            
            if not original:
                self.logger.debug(
                    f"Deleted message not in database: {original_msg_id}"
                )
                return None
            
            # Get details from database
            group_reply_id = original.get('group_id')
            sender = original.get('sender', 'unknown')
            is_outgoing = sender == 'you'
            
            if not group_reply_id:
                self.logger.warning("No group message ID for delete reference")
                return None
            
            # Build delete notification
            delete_text = self._build_delete_message(original)
            
            # Send delete notification via appropriate bot
            group_msg_id = await self.bot_manager.send_text(
                text=delete_text,
                is_outgoing=is_outgoing,
                reply_to=group_reply_id
            )
            
            # Mark as deleted in database
            await self.db.mark_deleted(original_msg_id)
            
            self.logger.debug(f"🗑️ Delete notification sent for: {original_msg_id}")
            
            return group_msg_id
            
        except Exception as e:
            self.logger.error(f"Failed to handle delete: {e}")
            return None
    
    def _build_delete_message(self, original: dict) -> str:
        """
        Build delete notification message.
        
        Args:
            original: Original message data from database
            
        Returns:
            str: Formatted delete notification
        """
        content_preview = original.get('content', '[Unknown content]')
        
        # Truncate if too long
        if len(content_preview) > 100:
            content_preview = content_preview[:100] + "..."
        
        has_media = original.get('has_media', False)
        media_label = " [Had Media]" if has_media else ""
        
        return f"{self.DELETE_PREFIX}{media_label}"
    
    async def handle_bulk_delete(self, message_ids: list) -> int:
        """
        Handle multiple message deletions at once.
        
        Args:
            message_ids: List of deleted message IDs
            
        Returns:
            int: Number of successfully handled deletions
        """
        success_count = 0
        
        for msg_id in message_ids:
            result = await self.handle(msg_id)
            if result:
                success_count += 1
        
        return success_count
