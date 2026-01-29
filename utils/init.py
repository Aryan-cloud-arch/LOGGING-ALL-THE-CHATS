"""
Utilities Package
=================
Power-packed utility functions for the Telegram Mirror Bot.

Modules:
    - helpers: General utility functions
    - media_utils: Media processing utilities
    - logger: Advanced logging system
    
Features:
    ✅ Async utilities
    ✅ Performance optimized
    ✅ Error resilient
    ✅ Memory efficient
    ✅ Thread-safe operations
"""

from .helpers import (
    format_file_size,
    sanitize_filename,
    get_message_link,
    parse_phone_number,
    validate_telegram_id,
    retry_async,
    RateLimiter,
    TimeTracker,
    MemoryMonitor
)

from .media_utils import (
    get_temp_path,
    cleanup_temp,
    get_media_info,
    optimize_photo,
    compress_video,
    MediaProcessor,
    ThumbnailGenerator
)

from .logger import (
    get_logger,
    setup_logging,
    ColoredFormatter,
    LogStats
)

__version__ = "1.0.0"
__author__ = "Your Name"

__all__ = [
    # Helpers
    "format_file_size",
    "sanitize_filename",
    "get_message_link",
    "parse_phone_number",
    "validate_telegram_id",
    "retry_async",
    "RateLimiter",
    "TimeTracker",
    "MemoryMonitor",
    
    # Media Utils
    "get_temp_path",
    "cleanup_temp",
    "get_media_info",
    "optimize_photo",
    "compress_video",
    "MediaProcessor",
    "ThumbnailGenerator",
    
    # Logger
    "get_logger",
    "setup_logging",
    "ColoredFormatter",
    "LogStats"
]
