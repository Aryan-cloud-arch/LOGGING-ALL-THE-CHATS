"""
Monitor
=======
Main monitor that watches your DM conversation
and coordinates forwarding to backup group.
"""

import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument
)

from config.settings import Settings
from database.operations import DatabaseOperations
from utils.logger import get_logger
from .bots import BotManager

logger = get_logger(__name__)


class Monitor:
    """
    Main monitor class that watches DM conversations.
    
    Attributes:
        client: TelegramClient for your account
        bot_manager: Manager for both bots
        db: Database operations
        settings: Configuration settings
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize monitor with settings.
        
        Args:
            settings: Configuration settings object
        """
        self.settings = settings
        self.client: TelegramClient = None
        self.bot_manager: BotManager = None
        self.db: DatabaseOperations = None
        self._running = False
        
        # Import handlers here to avoid circular imports
        self.handlers = None
    
    async def initialize(self) -> bool:
        """
        Initialize monitor, bots, and database.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize YOUR account (monitor)
            self.client = TelegramClient(
                session=f"sessions/monitor_{self.settings.YOUR_PHONE}",
                api_id=self.settings.API_ID,
                api_hash=self.settings.API_HASH
            )
            
            await self.client.start(phone=self.settings.YOUR_PHONE)
            logger.info("✅ Monitor account connected")
            
            # Initialize bot manager
            self.bot_manager = BotManager(self.settings)
            await self.bot_manager.initialize()
            
            # Initialize database
            self.db = DatabaseOperations(self.settings.MONGO_URI)
            await self.db.connect()
            
            # Setup handlers
            await self._setup_handlers()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Monitor initialization failed: {e}")
            return False
    
    async def _setup_handlers(self) -> None:
        """Register all event handlers."""
        from src.handlers import (
            MessageHandler,
            MediaHandler,
            ViewOnceHandler,
            EditHandler,
            DeleteHandler,
            ReplyHandler
        )
        
        # Initialize handlers with dependencies
        self.handlers = {
            'message': MessageHandler(self.bot_manager, self.db),
            'media': MediaHandler(self.bot_manager, self.db, self.client),
            'view_once': ViewOnceHandler(self.bot_manager, self.db, self.client),
            'edit': EditHandler(self.bot_manager, self.db),
            'delete': DeleteHandler(self.bot_manager, self.db),
            'reply': ReplyHandler(self.bot_manager, self.db)
        }
        
        # Register new message handler
        @self.client.on(events.NewMessage(chats=self.settings.HER_USER_ID))
        async def on_new_message(event):
            await self._handle_new_message(event)
        
        # Register edit handler
        @self.client.on(events.MessageEdited(chats=self.settings.HER_USER_ID))
        async def on_message_edited(event):
            await self._handle_edit(event)
        
        # Register delete handler
        @self.client.on(events.MessageDeleted(chats=self.settings.HER_USER_ID))
        async def on_message_deleted(event):
            await self._handle_delete(event)
        
        logger.info("✅ Event handlers registered")
    
    async def _handle_new_message(self, event) -> None:
        """
        Handle new incoming/outgoing message.
        
        Args:
            event: Telethon new message event
        """
        try:
            msg = event.message
            is_outgoing = msg.out
            
            # Check if view-once media
            if self._is_view_once(msg):
                group_msg_id = await self.handlers['view_once'].handle(
                    msg, is_outgoing
                )
            
            # Check if has media
            elif msg.media:
                group_msg_id = await self.handlers['media'].handle(
                    msg, is_outgoing
                )
            
            # Text message
            else:
                # Check if it's a reply
                reply_to_group_id = None
                if msg.reply_to_msg_id:
                    reply_to_group_id = await self.handlers['reply'].get_group_reply_id(
                        msg.reply_to_msg_id
                    )
                
                group_msg_id = await self.handlers['message'].handle(
                    msg, is_outgoing, reply_to_group_id
                )
            
            # Save to database
            await self.db.save_message(
                original_id=msg.id,
                group_id=group_msg_id,
                sender='you' if is_outgoing else 'her',
                content=msg.text or "[Media]",
                has_media=bool(msg.media),
                reply_to_original=msg.reply_to_msg_id
            )
            
            logger.info(f"✅ Message {msg.id} → {group_msg_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    async def _handle_edit(self, event) -> None:
        """
        Handle message edit event.
        
        Args:
            event: Telethon message edited event
        """
        try:
            msg = event.message
            is_outgoing = msg.out
            
            await self.handlers['edit'].handle(msg, is_outgoing)
            logger.info(f"✏️ Edit detected: {msg.id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling edit: {e}")
    
    async def _handle_delete(self, event) -> None:
        """
        Handle message delete event.
        
        Args:
            event: Telethon message deleted event
        """
        try:
            for msg_id in event.deleted_ids:
                await self.handlers['delete'].handle(msg_id)
                logger.info(f"🗑️ Delete detected: {msg_id}")
                
        except Exception as e:
            logger.error(f"❌ Error handling delete: {e}")
    
    def _is_view_once(self, msg) -> bool:
        """
        Check if message contains view-once media.
        
        Args:
            msg: Telethon message object
            
        Returns:
            bool: True if view-once media
        """
        if not msg.media:
            return False
        
        # Check for TTL (self-destructing)
        if hasattr(msg.media, 'ttl_seconds') and msg.media.ttl_seconds:
            return True
        
        # Check photo
        if isinstance(msg.media, MessageMediaPhoto):
            if hasattr(msg.media, 'ttl_seconds') and msg.media.ttl_seconds:
                return True
        
        # Check document/video
        if isinstance(msg.media, MessageMediaDocument):
            if hasattr(msg.media, 'ttl_seconds') and msg.media.ttl_seconds:
                return True
        
        return False
    
    async def catch_up(self) -> None:
        """
        Catch up on messages sent while bot was offline.
        Fetches from last processed message ID.
        """
        logger.info("🔄 Checking for missed messages...")
        
        try:
            # Get last processed message ID from database
            last_id = await self.db.get_last_processed_id()
            
            if not last_id:
                logger.info("📭 No previous messages found. Starting fresh.")
                return
            
            logger.info(f"📍 Last processed: {last_id}")
            
            # Fetch all messages after last_id
            missed_count = 0
            
            async for msg in self.client.iter_messages(
                self.settings.HER_USER_ID,
                min_id=last_id,
                reverse=True  # Chronological order
            ):
                # Skip if already processed
                if await self.db.message_exists(msg.id):
                    continue
                
                # Create fake event for handler
                event = type('Event', (), {'message': msg})()
                await self._handle_new_message(event)
                
                missed_count += 1
                await asyncio.sleep(0.5)  # Rate limit protection
            
            if missed_count > 0:
                logger.info(f"✅ Caught up {missed_count} missed messages")
            else:
                logger.info("✅ No missed messages")
                
        except Exception as e:
            logger.error(f"❌ Catch up failed: {e}")
    
    async def run(self) -> None:
        """Start the monitor and run until disconnected."""
        if not self.client:
            raise RuntimeError("Monitor not initialized. Call initialize() first.")
        
        self._running = True
        
        # Catch up on missed messages first
        await self.catch_up()
        
        logger.info("🚀 Monitor started. Watching for messages...")
        logger.info(f"👤 Monitoring chat with: {self.settings.HER_USER_ID}")
        logger.info(f"📦 Backup group: {self.settings.GROUP_ID}")
        logger.info("=" * 50)
        
        # Run until disconnected
        await self.client.run_until_disconnected()
    
    async def stop(self) -> None:
        """Stop the monitor gracefully."""
        self._running = False
        
        if self.bot_manager:
            await self.bot_manager.disconnect()
        
        if self.client:
            await self.client.disconnect()
            logger.info("🛑 Monitor stopped")
        
        if self.db:
            await self.db.disconnect()
