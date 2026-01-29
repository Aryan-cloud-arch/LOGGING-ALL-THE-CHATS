"""
Base Handler
============
Abstract base class for all handlers.
Provides common functionality and interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any

from src.bots import BotManager
from database.operations import DatabaseOperations
from utils.logger import get_logger


class BaseHandler(ABC):
    """
    Abstract base class for all message handlers.
    
    Attributes:
        bot_manager: Manager for bot clients
        db: Database operations instance
        logger: Logger instance for this handler
    """
    
    def __init__(
        self,
        bot_manager: BotManager,
        db: DatabaseOperations
    ):
        """
        Initialize base handler.
        
        Args:
            bot_manager: Bot manager instance
            db: Database operations instance
        """
        self.bot_manager = bot_manager
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def handle(self, *args, **kwargs) -> Optional[int]:
        """
        Handle the event. Must be implemented by subclasses.
        
        Returns:
            Optional[int]: Group message ID if successful
        """
        pass
    
    def get_sender_label(self, is_outgoing: bool) -> str:
        """
        Get formatted sender label.
        
        Args:
            is_outgoing: True if message is from you
            
        Returns:
            str: Formatted sender label
        """
        name = self.bot_manager.get_sender_name(is_outgoing)
        return f"👤 {name}"
    
    def get_timestamp_label(self, timestamp) -> str:
        """
        Format timestamp for display.
        
        Args:
            timestamp: Message timestamp
            
        Returns:
            str: Formatted time string
        """
        return timestamp.strftime("%I:%M %p")
