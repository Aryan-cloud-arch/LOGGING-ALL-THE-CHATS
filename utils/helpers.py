"""
Helper Utilities
================
General-purpose utility functions and classes.
Performance-optimized and production-ready.
"""

import os
import re
import asyncio
import time
import psutil
import functools
from typing import (
    Optional, 
    Union, 
    Dict, 
    Any, 
    Callable, 
    TypeVar, 
    List,
    Tuple
)
from datetime import datetime, timedelta
from pathlib import Path

import phonenumbers
from phonenumbers import NumberParseException

from .logger import get_logger

logger = get_logger(__name__)

# Type definitions
T = TypeVar('T')
AsyncFunc = TypeVar('AsyncFunc', bound=Callable)


# ==================== FORMATTING UTILITIES ====================

def format_file_size(bytes_size: int) -> str:
    """
    Format bytes to human-readable size.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.5 MB")
    
    Examples:
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            if unit == 'B':
                return f"{bytes_size:.0f} {unit}"
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.1f} PB"


def format_duration(seconds: Union[int, float]) -> str:
    """
    Format seconds to human-readable duration.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration (e.g., "1h 23m 45s")
    
    Examples:
        >>> format_duration(3665)
        '1h 1m 5s'
        >>> format_duration(45)
        '45s'
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def format_timestamp(
    dt: datetime, 
    format_type: str = "full"
) -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime object
        format_type: 'full', 'date', 'time', or 'relative'
        
    Returns:
        str: Formatted timestamp
    """
    if format_type == "full":
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif format_type == "date":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time":
        return dt.strftime("%H:%M:%S")
    elif format_type == "relative":
        delta = datetime.utcnow() - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"
    
    return str(dt)


# ==================== VALIDATION UTILITIES ====================

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe filesystem usage.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        str: Sanitized filename
    
    Examples:
        >>> sanitize_filename("my/file<name>.txt")
        'my_file_name_.txt'
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Truncate if too long
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    # Ensure not empty
    if not filename:
        filename = "unnamed"
    
    return filename


def validate_telegram_id(user_id: Union[str, int]) -> Tuple[bool, Optional[int]]:
    """
    Validate Telegram user/chat ID.
    
    Args:
        user_id: User or chat ID to validate
        
    Returns:
        Tuple[bool, Optional[int]]: (is_valid, parsed_id)
    
    Examples:
        >>> validate_telegram_id("123456789")
        (True, 123456789)
        >>> validate_telegram_id("invalid")
        (False, None)
    """
    try:
        # Convert to int
        if isinstance(user_id, str):
            # Remove @ if present
            user_id = user_id.lstrip('@')
            
            # Check if numeric
            if not user_id.lstrip('-').isdigit():
                return False, None
            
            user_id = int(user_id)
        
        # Telegram IDs are 32-bit or 64-bit integers
        if abs(user_id) > 10**15:
            return False, None
        
        return True, user_id
        
    except (ValueError, TypeError):
        return False, None


def parse_phone_number(
    phone: str, 
    region: str = None
) -> Tuple[bool, Optional[str]]:
    """
    Parse and validate phone number.
    
    Args:
        phone: Phone number string
        region: ISO country code (e.g., 'US')
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, formatted_number)
    
    Examples:
        >>> parse_phone_number("+1234567890")
        (True, "+1 234-567-890")
    """
    try:
        # Parse number
        parsed = phonenumbers.parse(phone, region)
        
        # Validate
        if not phonenumbers.is_valid_number(parsed):
            return False, None
        
        # Format international
        formatted = phonenumbers.format_number(
            parsed, 
            phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
        
        return True, formatted
        
    except NumberParseException:
        return False, None


# ==================== TELEGRAM UTILITIES ====================

def get_message_link(
    chat_id: Union[str, int],
    message_id: int,
    is_private: bool = False
) -> str:
    """
    Generate Telegram message link.
    
    Args:
        chat_id: Chat username or ID
        message_id: Message ID
        is_private: Whether chat is private
        
    Returns:
        str: Message link
    
    Examples:
        >>> get_message_link("@mychannel", 123)
        'https://t.me/mychannel/123'
    """
    if is_private:
        # Private chats use different format
        return f"https://t.me/c/{str(chat_id).lstrip('-100')}/{message_id}"
    
    # Public channel/group
    chat_id = str(chat_id).lstrip('@')
    return f"https://t.me/{chat_id}/{message_id}"


def parse_telegram_link(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse Telegram message link.
    
    Args:
        url: Telegram message URL
        
    Returns:
        Optional[Dict]: Parsed components or None
    """
    # Pattern for public channels
    public_pattern = r"https?://t\.me/([^/]+)/(\d+)"
    
    # Pattern for private channels
    private_pattern = r"https?://t\.me/c/(\d+)/(\d+)"
    
    # Try public pattern
    match = re.match(public_pattern, url)
    if match:
        return {
            "type": "public",
            "chat": match.group(1),
            "message_id": int(match.group(2))
        }
    
    # Try private pattern
    match = re.match(private_pattern, url)
    if match:
        return {
            "type": "private",
            "chat_id": f"-100{match.group(1)}",
            "message_id": int(match.group(2))
        }
    
    return None


# ==================== ASYNC UTILITIES ====================

def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,)
) -> Callable:
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Exceptions to catch
        
    Returns:
        Decorated function
    
    Usage:
        @retry_async(max_attempts=5, delay=2.0)
        async def unstable_api_call():
            ...
    """
    def decorator(func: AsyncFunc) -> AsyncFunc:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed, "
                        f"retrying in {current_delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


# ==================== RATE LIMITING ====================

class RateLimiter:
    """
    Async rate limiter using token bucket algorithm.
    
    Features:
        - Token bucket algorithm
        - Async-safe
        - Configurable burst size
        - Auto-refill
    """
    
    def __init__(
        self,
        rate: int,
        per: float = 1.0,
        burst: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of allowed calls
            per: Time period in seconds
            burst: Maximum burst size (default: same as rate)
        """
        self.rate = rate
        self.per = per
        self.burst = burst or rate
        self.tokens = self.burst
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            float: Time waited in seconds
        """
        async with self._lock:
            wait_time = await self._acquire_tokens(tokens)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                wait_time = await self._acquire_tokens(tokens)
            
            return wait_time
    
    async def _acquire_tokens(self, tokens: int) -> float:
        """
        Internal method to acquire tokens.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            float: Wait time if tokens not available
        """
        # Refill tokens based on time passed
        now = time.monotonic()
        elapsed = now - self.last_refill
        
        # Add new tokens
        new_tokens = elapsed * (self.rate / self.per)
        self.tokens = min(self.burst, self.tokens + new_tokens)
        self.last_refill = now
        
        # Check if enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0
        
        # Calculate wait time
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / (self.rate / self.per)
        
        return wait_time
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        return self.tokens
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass


# ==================== TIME TRACKING ====================

class TimeTracker:
    """
    Track execution times for performance monitoring.
    
    Features:
        - Context manager support
        - Statistics calculation
        - Multiple timer support
    """
    
    def __init__(self, name: str = "default"):
        """
        Initialize time tracker.
        
        Args:
            name: Tracker name for identification
        """
        self.name = name
        self.times: List[float] = []
        self.start_time: Optional[float] = None
        self.current_elapsed: float = 0.0
    
    def start(self) -> 'TimeTracker':
        """Start timing."""
        self.start_time = time.perf_counter()
        return self
    
    def stop(self) -> float:
        """
        Stop timing and record elapsed time.
        
        Returns:
            float: Elapsed time in seconds
        """
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        self.current_elapsed = time.perf_counter() - self.start_time
        self.times.append(self.current_elapsed)
        self.start_time = None
        
        return self.current_elapsed
    
    @property
    def elapsed(self) -> float:
        """Get current elapsed time."""
        if self.start_time is not None:
            return time.perf_counter() - self.start_time
        return self.current_elapsed
    
    @property
    def average(self) -> float:
        """Get average execution time."""
        if not self.times:
            return 0.0
        return sum(self.times) / len(self.times)
    
    @property
    def total(self) -> float:
        """Get total execution time."""
        return sum(self.times)
    
    @property
    def count(self) -> int:
        """Get number of measurements."""
        return len(self.times)
    
    def reset(self) -> None:
        """Reset all measurements."""
        self.times.clear()
        self.start_time = None
        self.current_elapsed = 0.0
    
    def stats(self) -> Dict[str, float]:
        """
        Get statistics.
        
        Returns:
            Dict with min, max, average, total times
        """
        if not self.times:
            return {
                "min": 0.0,
                "max": 0.0,
                "average": 0.0,
                "total": 0.0,
                "count": 0
            }
        
        return {
            "min": min(self.times),
            "max": max(self.times),
            "average": self.average,
            "total": self.total,
            "count": self.count
        }
    
    def __enter__(self) -> 'TimeTracker':
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def __str__(self) -> str:
        """String representation."""
        if self.times:
            return f"TimeTracker({self.name}): {self.average:.3f}s avg, {self.count} calls"
        return f"TimeTracker({self.name}): No measurements"


# ==================== MEMORY MONITORING ====================

class MemoryMonitor:
    """
    Monitor memory usage and detect leaks.
    
    Features:
        - Process memory tracking
        - Garbage collection stats
        - Memory leak detection
        - Threshold alerts
    """
    
    def __init__(
        self,
        threshold_mb: float = 500.0,
        check_interval: float = 60.0
    ):
        """
        Initialize memory monitor.
        
        Args:
            threshold_mb: Memory threshold in MB
            check_interval: Check interval in seconds
        """
        self.threshold_bytes = threshold_mb * 1024 * 1024
        self.check_interval = check_interval
        self.process = psutil.Process()
        self.measurements: List[Dict[str, Any]] = []
        self._monitoring = False
        self._task: Optional[asyncio.Task] = None
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get current memory information.
        
        Returns:
            Dict with memory statistics
        """
        mem_info = self.process.memory_info()
        
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": self.process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "timestamp": datetime.utcnow()
        }
    
    async def start_monitoring(self) -> None:
        """Start async memory monitoring."""
        if self._monitoring:
            logger.warning("Memory monitoring already started")
            return
        
        self._monitoring = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("🔍 Memory monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self._monitoring = False
        
        if self._task:
            self._task.cancel()
            
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Memory monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Internal monitoring loop."""
        while self._monitoring:
            try:
                info = self.get_memory_info()
                self.measurements.append(info)
                
                # Keep only last 100 measurements
                if len(self.measurements) > 100:
                    self.measurements.pop(0)
                
                # Check threshold
                if info["rss_mb"] * 1024 * 1024 > self.threshold_bytes:
                    logger.warning(
                        f"⚠️ Memory threshold exceeded: {info['rss_mb']:.1f} MB"
                    )
                
                # Check for potential leak (continuous growth)
                if self._detect_leak():
                    logger.error("🚨 Potential memory leak detected!")
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def _detect_leak(self, window_size: int = 10) -> bool:
        """
        Detect potential memory leak.
        
        Args:
            window_size: Number of measurements to analyze
            
        Returns:
            bool: True if potential leak detected
        """
        if len(self.measurements) < window_size:
            return False
        
        recent = self.measurements[-window_size:]
        
        # Check if memory is continuously increasing
        increasing_count = 0
        for i in range(1, len(recent)):
            if recent[i]["rss_mb"] > recent[i-1]["rss_mb"]:
                increasing_count += 1
        
        # If 80% of measurements show increase, possible leak
        return increasing_count > (window_size * 0.8)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Returns:
            Dict with memory stats
        """
        if not self.measurements:
            return {"error": "No measurements available"}
        
        rss_values = [m["rss_mb"] for m in self.measurements]
        
        return {
            "current_mb": rss_values[-1],
            "min_mb": min(rss_values),
            "max_mb": max(rss_values),
            "average_mb": sum(rss_values) / len(rss_values),
            "measurements": len(self.measurements),
            "potential_leak": self._detect_leak()
        }


# ==================== PATH UTILITIES ====================

def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if not.
    
    Args:
        path: Directory path
        
    Returns:
        Path: Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_root() -> Path:
    """
    Get project root directory.
    
    Returns:
        Path: Project root path
    """
    return Path(__file__).parent.parent


def cleanup_old_files(
    directory: Union[str, Path],
    days: int = 7,
    pattern: str = "*"
) -> int:
    """
    Clean up old files from directory.
    
    Args:
        directory: Directory to clean
        days: Delete files older than this
        pattern: File pattern to match
        
    Returns:
        int: Number of files deleted
    """
    directory = Path(directory)
    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0
    
    for file in directory.glob(pattern):
        if file.is_file():
            # Check file age
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            
            if mtime < cutoff:
                try:
                    file.unlink()
                    deleted += 1
                    logger.debug(f"Deleted old file: {file}")
                except Exception as e:
                    logger.error(f"Failed to delete {file}: {e}")
    
    return deleted
