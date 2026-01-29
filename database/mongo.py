"""
MongoDB Manager
===============
Handles MongoDB connection pooling and lifecycle.
Implements singleton pattern for connection reuse.
"""

import asyncio
from typing import Optional, Dict, Any
from urllib.parse import quote_plus

import motor.motor_asyncio
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    ConfigurationError
)

from utils.logger import get_logger

logger = get_logger(__name__)


class MongoManager:
    """
    MongoDB connection manager with automatic retry and pooling.
    
    Features:
        - Singleton pattern for connection reuse
        - Automatic reconnection on failure
        - Connection pooling
        - Health checks
        - Graceful shutdown
    """
    
    _instance: Optional['MongoManager'] = None
    _lock = asyncio.Lock()
    
    # Connection settings
    MAX_POOL_SIZE = 10
    MIN_POOL_SIZE = 2
    SERVER_SELECTION_TIMEOUT = 5000  # ms
    CONNECT_TIMEOUT = 10000  # ms
    RETRY_WRITES = True
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton instance."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, connection_uri: str = None):
        """
        Initialize MongoDB manager.
        
        Args:
            connection_uri: MongoDB connection string
        """
        # Skip if already initialized
        if hasattr(self, '_initialized'):
            return
        
        self.connection_uri = connection_uri
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.database: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        self._connected = False
        self._initialized = True
    
    async def connect(
        self,
        database_name: str = "telegram_mirror",
        retry_attempts: int = 3
    ) -> bool:
        """
        Establish connection to MongoDB.
        
        Args:
            database_name: Name of database to use
            retry_attempts: Number of connection attempts
            
        Returns:
            bool: True if connected successfully
        """
        async with self._lock:
            if self._connected:
                logger.debug("Already connected to MongoDB")
                return True
            
            for attempt in range(1, retry_attempts + 1):
                try:
                    logger.info(f"📡 Connecting to MongoDB (attempt {attempt}/{retry_attempts})...")
                    
                    # Create client with optimized settings
                    self.client = motor.motor_asyncio.AsyncIOMotorClient(
                        self.connection_uri,
                        maxPoolSize=self.MAX_POOL_SIZE,
                        minPoolSize=self.MIN_POOL_SIZE,
                        serverSelectionTimeoutMS=self.SERVER_SELECTION_TIMEOUT,
                        connectTimeoutMS=self.CONNECT_TIMEOUT,
                        retryWrites=self.RETRY_WRITES
                    )
                    
                    # Test connection
                    await self.client.admin.command('ping')
                    
                    # Select database
                    self.database = self.client[database_name]
                    
                    # Create indexes
                    await self._create_indexes()
                    
                    self._connected = True
                    logger.info(f"✅ Connected to MongoDB: {database_name}")
                    
                    return True
                    
                except ServerSelectionTimeoutError:
                    logger.warning(f"⏱️ Connection timeout (attempt {attempt})")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
                except ConnectionFailure as e:
                    logger.error(f"❌ Connection failed: {e}")
                    await asyncio.sleep(2 ** attempt)
                    
                except Exception as e:
                    logger.error(f"❌ Unexpected error: {e}")
                    if attempt == retry_attempts:
                        raise
            
            logger.error(f"❌ Failed to connect after {retry_attempts} attempts")
            return False
    
    async def _create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # Messages collection indexes
            messages = self.database.messages
            await messages.create_index("original_id", unique=True)
            await messages.create_index("group_id")
            await messages.create_index("sender")
            await messages.create_index("timestamp")
            await messages.create_index([("timestamp", -1)])  # Descending for latest
            
            # Edit history indexes
            edits = self.database.edit_history
            await edits.create_index("original_id")
            await edits.create_index("edit_time")
            
            # Reply chains indexes
            replies = self.database.reply_chains
            await replies.create_index("original_id")
            await replies.create_index("reply_to_id")
            
            # System state indexes
            state = self.database.system_state
            await state.create_index("key", unique=True)
            
            logger.debug("📇 Database indexes created")
            
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from MongoDB."""
        async with self._lock:
            if self.client and self._connected:
                self.client.close()
                self._connected = False
                logger.info("🔌 Disconnected from MongoDB")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on database connection.
        
        Returns:
            Dict containing health status and metrics
        """
        try:
            if not self._connected:
                return {
                    "healthy": False,
                    "status": "disconnected",
                    "error": "Not connected to database"
                }
            
            # Ping database
            start = asyncio.get_event_loop().time()
            await self.client.admin.command('ping')
            latency = (asyncio.get_event_loop().time() - start) * 1000
            
            # Get database stats
            stats = await self.database.command("dbStats")
            
            return {
                "healthy": True,
                "status": "connected",
                "latency_ms": round(latency, 2),
                "database": self.database.name,
                "collections": stats.get("collections", 0),
                "documents": stats.get("objects", 0),
                "size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "status": "error",
                "error": str(e)
            }
    
    def get_collection(self, name: str):
        """
        Get collection by name.
        
        Args:
            name: Collection name
            
        Returns:
            AsyncIOMotorCollection instance
        """
        if not self._connected:
            raise ConnectionError("Not connected to MongoDB")
        
        return self.database[name]
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Convenience functions
async def get_mongo_manager(uri: str = None) -> MongoManager:
    """
    Get or create MongoDB manager instance.
    
    Args:
        uri: MongoDB connection URI
        
    Returns:
        MongoManager: Singleton instance
    """
    manager = MongoManager(uri)
    if not manager.is_connected:
        await manager.connect()
    return manager
