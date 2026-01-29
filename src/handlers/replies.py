"""
Reply Handler
=============
Manages reply chain relationships between original and mirrored messages.
"""

from typing import Optional

from .base import BaseHandler


class ReplyHandler(BaseHandler):
    """
    Handler for reply chain management.
    
    Responsibilities:
        - Map original reply IDs to group message IDs
        - Maintain reply relationships in mirrored conversation
        - Handle nested reply chains
    """
    
    async def handle(
        self,
        msg,
        is_outgoing: bool,
        original_reply_id: int
    ) -> Optional[int]:
        """
        Handle reply relationship.
        
        Args:
            msg: Message object
            is_outgoing: True if you sent the message
            original_reply_id: ID of message being replied to in DM
            
        Returns:
            Optional[int]: Group message ID of the reply target
        """
        try:
            # Get the group message ID for the original reply target
            group_reply_id = await self.get_group_reply_id(original_reply_id)
            
            if group_reply_id:
                self.logger.debug(
                    f"🔗 Reply chain: {original_reply_id} → {group_reply_id}"
                )
            
            return group_reply_id
            
        except Exception as e:
            self.logger.error(f"Failed to handle reply: {e}")
            return None
    
    async def get_group_reply_id(
        self,
        original_msg_id: int
    ) -> Optional[int]:
        """
        Get the group message ID for a given original message ID.
        
        Args:
            original_msg_id: Original message ID in DM
            
        Returns:
            Optional[int]: Corresponding message ID in group
        """
        try:
            message_data = await self.db.get_message(original_msg_id)
            
            if message_data:
                return message_data.get('group_id')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get group reply ID: {e}")
            return None
    
    async def build_reply_chain(
        self,
        msg_id: int,
        max_depth: int = 10
    ) -> list:
        """
        Build complete reply chain for a message.
        
        Args:
            msg_id: Starting message ID
            max_depth: Maximum chain depth to traverse
            
        Returns:
            list: List of message IDs in the chain (oldest to newest)
        """
        chain = []
        current_id = msg_id
        depth = 0
        
        try:
            while current_id and depth < max_depth:
                message_data = await self.db.get_message(current_id)
                
                if not message_data:
                    break
                
                chain.insert(0, {
                    'original_id': current_id,
                    'group_id': message_data.get('group_id'),
                    'sender': message_data.get('sender'),
                    'content': message_data.get('content', '')[:50]
                })
                
                # Move to parent message
                current_id = message_data.get('reply_to_original')
                depth += 1
            
            return chain
            
        except Exception as e:
            self.logger.error(f"Failed to build reply chain: {e}")
            return chain
    
    async def save_reply_mapping(
        self,
        original_id: int,
        original_reply_to: int,
        group_id: int,
        group_reply_to: int
    ) -> bool:
        """
        Save reply mapping to database.
        
        Args:
            original_id: Original message ID
            original_reply_to: Original reply target ID
            group_id: Group message ID
            group_reply_to: Group reply target ID
            
        Returns:
            bool: True if saved successfully
        """
        try:
            await self.db.save_reply_mapping(
                original_id=original_id,
                original_reply_to=original_reply_to,
                group_id=group_id,
                group_reply_to=group_reply_to
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save reply mapping: {e}")
            return False
