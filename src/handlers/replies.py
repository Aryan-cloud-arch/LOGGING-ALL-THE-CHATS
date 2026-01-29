from typing import Optional
from .base import BaseHandler

class ReplyHandler(BaseHandler):
    async def handle(self, msg, is_outgoing: bool, original_reply_id: int) -> Optional[int]:
        try:
            group_reply_id = await self.get_group_reply_id(original_reply_id)
            if group_reply_id:
                self.logger.debug(f"Reply chain: {original_reply_id} → {group_reply_id}")
            return group_reply_id
        except Exception as e:
            self.logger.error(f"Failed to handle reply: {e}")
            return None

    async def get_group_reply_id(self, original_msg_id: int) -> Optional[int]:
        try:
            message_data = await self.db.get_message(original_msg_id)
            if message_data:
                return message_data.get('group_id')
            return None
        except Exception as e:
            self.logger.error(f"Failed to get group reply ID: {e}")
            return None
