"""
Logger Utilities
================
Advanced logging system with colors, rotation, and statistics.
Production-ready logging for Telegram Mirror Bot.
"""

import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Union
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from collections import defaultdict
import json

from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colors
init(autoreset=True)


# ==================== CUSTOM FORMATTER ====================

class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter with emoji indicators.
    
    Features:
        - Color-coded log levels
        - Emoji indicators
        - Clean formatting
        - Time stamps
    """
    
    # Color mapping
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }
    
    # Emoji mapping
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def __init__(
        self,
        use_colors: bool = True,
        use_emojis: bool = True,
        show_time: bool = True
    ):
        """
        Initialize colored formatter.
        
        Args:
            use_colors: Enable colors
            use_emojis: Enable emoji indicators
            show_time: Show timestamps
        """
        self.use_colors = use_colors
        self.use_emojis = use_emojis
        
        # Build format string
        fmt_parts = []
        
        if show_time:
            fmt_parts.append('%(asctime)s')
        
        if use_emojis:
            fmt_parts.append('%(emoji)s')
        
        fmt_parts.extend([
            '%(levelname)-8s',
            '%(name)s',
            '%(message)s'
        ])
        
        fmt = ' | '.join(fmt_parts)
        super().__init__(fmt, datefmt='%H:%M:%S')
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors and emojis.
        
        Args:
            record: Log record to format
            
        Returns:
            str: Formatted log message
        """
        # Add emoji to record
        if self.use_emojis:
            record.emoji = self.EMOJIS.get(record.levelname, '')
        
        # Format base message
        message = super().format(record)
        
        # Add colors
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            
            # Color the level name
            message = message.replace(
                record.levelname,
                f"{color}{record.levelname}{Style.RESET_ALL}"
            )
        
        return message


# ==================== JSON FORMATTER ====================

class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Features:
        - JSON output
        - Additional metadata
        - Error serialization
        - Easy parsing
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            str: JSON formatted log
        """
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename',
                'funcName', 'levelname', 'levelno', 'lineno',
                'module', 'msecs', 'message', 'pathname', 'process',
                'processName', 'relativeCreated', 'thread',
                'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                log_obj[key] = value
        
        return json.dumps(log_obj, ensure_ascii=False)


# ==================== LOG STATISTICS ====================

class LogStats:
    """
    Track logging statistics.
    
    Features:
        - Count by level
        - Error tracking
        - Performance metrics
        - Memory usage
    """
    
    def __init__(self):
        """Initialize log statistics."""
        self.counts = defaultdict(int)
        self.errors = []
        self.start_time = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def record(self, level: str, message: str) -> None:
        """
        Record log event.
        
        Args:
            level: Log level
            message: Log message
        """
        async with self._lock:
            self.counts[level] += 1
            
            if level in ('ERROR', 'CRITICAL'):
                self.errors.append({
                    'time': datetime.utcnow(),
                    'level': level,
                    'message': message[:200]  # Truncate long messages
                })
                
                # Keep only last 100 errors
                if len(self.errors) > 100:
                    self.errors.pop(0)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics.
        
        Returns:
            Dict with statistics
        """
        async with self._lock:
            uptime = datetime.utcnow() - self.start_time
            
            return {
                'uptime_seconds': uptime.total_seconds(),
                'total_logs': sum(self.counts.values()),
                'counts_by_level': dict(self.counts),
                'error_count': len(self.errors),
                'recent_errors': self.errors[-10:],  # Last 10 errors
                'logs_per_minute': self._calculate_rate()
            }
    
    def _calculate_rate(self) -> float:
        """Calculate logging rate."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        if uptime > 0:
            return (sum(self.counts.values()) / uptime) * 60
        
        return 0.0
    
    def reset(self) -> None:
        """Reset statistics."""
        self.counts.clear()
        self.errors.clear()
        self.start_time = datetime.utcnow()


# Global stats instance
_log_stats = LogStats()


# ==================== STATS HANDLER ====================

class StatsHandler(logging.Handler):
    """
    Handler that tracks statistics.
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Track log record in statistics.
        
        Args:
            record: Log record
        """
        # Run async task in background
        asyncio.create_task(
            _log_stats.record(record.levelname, record.getMessage())
        )


# ==================== SETUP FUNCTIONS ====================

def setup_logging(
    level: Union[str, int] = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True,
    use_json: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> None:
    """
    Setup logging configuration.
    
    Args:
        level: Logging level
        log_file: Log file path (optional)
        use_colors: Use colored output
        use_json: Use JSON formatting for file
        max_bytes: Max log file size
        backup_count: Number of backup files
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if use_colors:
        console_formatter = ColoredFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # Set formatter
        if use_json:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Add stats handler
    stats_handler = StatsHandler()
    stats_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(stats_handler)
    
    # Log setup complete
    logger = logging.getLogger(__name__)
    logger.info("🚀 Logging system initialized")
    
    if log_file:
        logger.info(f"📝 Logging to file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance for module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Shorten name for display
    if '.' in name:
        # Use last component only
        logger.name = name.split('.')[-1]
    
    return logger


def get_log_stats() -> LogStats:
    """
    Get global log statistics instance.
    
    Returns:
        LogStats: Global statistics
    """
    return _log_stats


# ==================== LOG UTILITIES ====================

async def cleanup_old_logs(
    log_dir: Union[str, Path] = "logs",
    days_to_keep: int = 30
) -> int:
    """
    Clean up old log files.
    
    Args:
        log_dir: Log directory
        days_to_keep: Keep logs newer than this
        
    Returns:
        int: Number of files deleted
    """
    log_dir = Path(log_dir)
    
    if not log_dir.exists():
        return 0
    
    deleted = 0
    cutoff = datetime.now().timestamp() - (days_to_keep * 86400)
    
    for log_file in log_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff:
            try:
                log_file.unlink()
                deleted += 1
            except Exception as e:
                logger = get_logger(__name__)
                logger.error(f"Failed to delete {log_file}: {e}")
    
    if deleted > 0:
        logger = get_logger(__name__)
        logger.info(f"🧹 Deleted {deleted} old log files")
    
    return deleted


def log_exception(
    logger: logging.Logger,
    exc: Exception,
    message: str = "Exception occurred"
) -> None:
    """
    Log exception with full traceback.
    
    Args:
        logger: Logger instance
        exc: Exception to log
        message: Additional message
    """
    logger.error(f"{message}: {exc}", exc_info=True)
