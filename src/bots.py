"""
Bot Manager
===========
Handles initialization and management of bot clients.
Uses Telethon for bots (MTProto) to bypass 50MB HTTP limit.
"""

from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError
)
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


class BotManager:
    """
    Manages both bot clients (@YourNameBot and @HerNameBot).
    
    Attributes:
        your_bot: TelegramClient for your messages
        her_bot: TelegramClient for her messages
        group_id: Target backup group ID
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize bot manager with settings.
        
        Args:
            settings: Configuration settings object
        """
        self.settings = settings
        self.your_bot: TelegramClient = None
        self.her_bot: TelegramClient = None
        self.group_id = settings.GROUP_ID
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize both bot clients.
        
        Returns:
            bool: True if both bots initialized successfully
        """
        try:
            # Initialize YOUR bot
            self.your_bot = TelegramClient(
                session=f"sessions/{self.settings.YOUR_BOT_NAME}",
                api_id=self.settings.API_ID,
                api_hash=self.settings.API_HASH
            )
            
            await self.your_bot.start(bot_token=self.settings.YOUR_BOT_TOKEN)
            logger.info(f"✅ {self.settings.YOUR_BOT_NAME} initialized")
            
            # Initialize HER bot
            self.her_bot = TelegramClient(
                session=f"sessions/{self.settings.HER_BOT_NAME}",
                api_id=self.settings.API_ID,
                api_hash=self.settings.API_HASH
            )
            
            await self.her_bot.start(bot_token=self.settings.HER_BOT_TOKEN)
            logger.info(f"✅ {self.settings.HER_BOT_NAME} initialized")
            
            # Verify both bots are in the group
            await self._verify_group_membership()
            
            self._initialized = True
            return True
            
        except AuthKeyUnregisteredError:
            logger.error("❌ Bot token is invalid or revoked")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize bots: {e}")
            return False
    
    async def _verify_group_membership(self) -> None:
        """
        Verify both bots are members of the backup group.
        
        Raises:
            ValueError: If bots are not in the group
        """
        try:
            # Check YOUR bot
            await self.your_bot.get_permissions(self.group_id)
            logger.info(f"✅ {self.settings.YOUR_BOT_NAME} is in group")
            
            # Check HER bot
            await self.her_bot.get_permissions(self.group_id)
            logger.info(f"✅ {self.settings.HER_BOT_NAME} is in group")
            
        except Exception as e:
            logger.error(f"❌ Bots not in group. Add both bots first!")
            raise ValueError(f"Bots not in group: {e}")
    
    def get_bot(self, is_outgoing: bool) -> TelegramClient:
        """
        Get appropriate bot based on message direction.
        
        Args:
            is_outgoing: True if message is from you
            
        Returns:
            TelegramClient: your_bot if outgoing, her_bot otherwise
        """
        if not self._initialized:
            raise RuntimeError("BotManager not initialized. Call initialize() first.")
        
        return self.your_bot if is_outgoing else self.her_bot
    
    def get_sender_name(self, is_outgoing: bool) -> str:
        """
        Get sender display name based on message direction.
        
        Args:
            is_outgoing: True if message is from you
            
        Returns:
            str: Sender's display name
        """
        return self.settings.YOUR_NAME if is_outgoing else self.settings.HER_NAME
    
    async def send_text(
        self,
        text: str,
        is_outgoing: bool,
        reply_to: int = None
    ) -> int:
        """
        Send text message via appropriate bot.
        
        Args:
            text: Message text
            is_outgoing: True if message is from you
            reply_to: Message ID to reply to (optional)
            
        Returns:
            int: Sent message ID in group
        """
        bot = self.get_bot(is_outgoing)
        
        message = await bot.send_message(
            entity=self.group_id,
            message=text,
            reply_to=reply_to
        )
        
        logger.debug(f"📤 Sent text via {self.get_sender_name(is_outgoing)}")
        return message.id
    
    async def send_media(
        self,
        media,
        is_outgoing: bool,
        caption: str = None,
        reply_to: int = None
    ) -> int:
        """
        Send media via appropriate bot (no download needed).
        
        Args:
            media: Media object from original message
            is_outgoing: True if message is from you
            caption: Optional caption
            reply_to: Message ID to reply to (optional)
            
        Returns:
            int: Sent message ID in group
        """
        bot = self.get_bot(is_outgoing)
        
        message = await bot.send_message(
            entity=self.group_id,
            message=caption or "",
            file=media,
            reply_to=reply_to
        )
        
        logger.debug(f"📤 Sent media via {self.get_sender_name(is_outgoing)}")
        return message.id
    
    async def send_file(
        self,
        file_path: str,
        is_outgoing: bool,
        caption: str = None,
        reply_to: int = None
    ) -> int:
        """
        Send file from disk via appropriate bot.
        Used for view-once media.
        
        Args:
            file_path: Path to file on disk
            is_outgoing: True if message is from you
            caption: Optional caption
            reply_to: Message ID to reply to (optional)
            
        Returns:
            int: Sent message ID in group
        """
        bot = self.get_bot(is_outgoing)
        
        message = await bot.send_file(
            entity=self.group_id,
            file=file_path,
            caption=caption,
            reply_to=reply_to
        )
        
        logger.debug(f"📤 Sent file via {self.get_sender_name(is_outgoing)}")
        return message.id
    
    async def disconnect(self) -> None:
        """Disconnect both bot clients gracefully."""
        if self.your_bot:
            await self.your_bot.disconnect()
            logger.info(f"🔌 {self.settings.YOUR_BOT_NAME} disconnected")
        
        if self.her_bot:
            await self.her_bot.disconnect()
            logger.info(f"🔌 {self.settings.HER_BOT_NAME} disconnected")
        
        self._initialized = False
