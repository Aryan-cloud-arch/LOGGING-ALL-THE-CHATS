"""
Database Package
================
MongoDB integration for message tracking and persistence.

Components:
    - MongoManager: Connection pool management
    - Models: Data schemas and validation
    - Operations: CRUD operations with retry logic
    
Features:
    ✅ Async MongoDB operations
    ✅ Automatic reconnection
    ✅ Connection pooling
    ✅ Index optimization
    ✅ Transaction support
"""

from .mongo import MongoManager
from .models import (
    MessageModel,
    EditHistoryModel,
    ReplyChainModel,
    SystemStateModel
)
from .operations import DatabaseOperations

__version__ = "1.0.0"

__all__ = [
    "MongoManager",
    "MessageModel",
    "EditHistoryModel",
    "ReplyChainModel",
    "SystemStateModel",
    "DatabaseOperations"
]
