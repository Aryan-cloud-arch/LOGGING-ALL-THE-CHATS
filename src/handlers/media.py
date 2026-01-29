from typing import Optional
from telethon.tl.types import Message
from .base import BaseHandler
import os

class MediaHandler(BaseHandler):
    def __init__(self, bot_manager, db, monitor_client):
        super().__init__(bot_manager, db)
        self.monitor = monitor_client

    async def handle(self, msg: Message, is_outgoing: bool, reply_to_group_id: Optional[int] = None) -> Optional[int]:
        try:
            # PHOTOS: Download & send via bot (for bot name display)
            if msg.photo:
                os.makedirs("temp", exist_ok=True)
                path = await self.monitor.download_media(msg, file=f"temp/photo_{msg.id}.jpg")
                if path:
                    bot = self.bot_manager.get_bot(is_outgoing)
                    sent = await bot.send_file(
                        entity=self.bot_manager.group_id,
                        file=path,
                        caption=msg.text or "",
                        reply_to=reply_to_group_id
                    )
                    os.remove(path)
                    return sent.id
            
            # VIDEOS/DOCS: Forward using YOUR account (INSTANT!)
            else:
                # Forward instantly via your account
                forwarded = await self.monitor.send_message(
                    entity=self.bot_manager.group_id,
                    message=msg  # This forwards the entire message including media!
                )
                
                # Add label via bot
                bot = self.bot_manager.get_bot(is_outgoing)
                sender = self.bot_manager.get_sender_name(is_outgoing)
                await bot.send_message(
                    entity=self.bot_manager.group_id,
                    message=f"👤 {sender}",
                    reply_to=forwarded.id
                )
                
                return forwarded.id
            
        except Exception as e:
            self.logger.error(f"Media error: {e}")
            return None
