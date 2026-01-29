"""
Media Utilities
===============
Media processing and management utilities.
Optimized for Telegram media handling.
"""

import os
import asyncio
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union
from datetime import datetime

import aiofiles
from PIL import Image, ImageOps
import ffmpeg

from .helpers import format_file_size, sanitize_filename, ensure_directory
from .logger import get_logger

logger = get_logger(__name__)


# ==================== PATH MANAGEMENT ====================

def get_temp_path(
    identifier: Union[str, int],
    extension: str = None
) -> str:
    """
    Generate temporary file path.
    
    Args:
        identifier: Unique identifier (e.g., message ID)
        extension: File extension (optional)
        
    Returns:
        str: Temporary file path
    """
    temp_dir = ensure_directory(Path("temp"))
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{identifier}"
    
    if extension:
        filename = f"{filename}.{extension.lstrip('.')}"
    
    return str(temp_dir / filename)


async def cleanup_temp(
    path: Optional[Union[str, Path]] = None,
    older_than_hours: int = 24
) -> int:
    """
    Clean up temporary files.
    
    Args:
        path: Specific file to delete or None for all old files
        older_than_hours: Delete files older than this
        
    Returns:
        int: Number of files deleted
    """
    if path:
        # Delete specific file
        try:
            path = Path(path)
            if path.exists():
                path.unlink()
                logger.debug(f"🗑️ Deleted temp file: {path}")
                return 1
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
        return 0
    
    # Clean old files
    temp_dir = Path("temp")
    if not temp_dir.exists():
        return 0
    
    deleted = 0
    cutoff = datetime.now().timestamp() - (older_than_hours * 3600)
    
    for file in temp_dir.iterdir():
        if file.is_file():
            if file.stat().st_mtime < cutoff:
                try:
                    file.unlink()
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file}: {e}")
    
    if deleted > 0:
        logger.info(f"🧹 Cleaned up {deleted} old temp files")
    
    return deleted


# ==================== MEDIA INFO ====================

async def get_media_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get detailed media file information.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Dict with media information
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {"error": "File not found"}
    
    info = {
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "size_formatted": format_file_size(file_path.stat().st_size),
        "mime_type": mimetypes.guess_type(str(file_path))[0],
        "modified": datetime.fromtimestamp(file_path.stat().st_mtime),
        "hash": await _calculate_file_hash(file_path)
    }
    
    # Get media-specific info
    mime = info["mime_type"] or ""
    
    if mime.startswith("image/"):
        info.update(await _get_image_info(file_path))
    elif mime.startswith("video/"):
        info.update(await _get_video_info(file_path))
    elif mime.startswith("audio/"):
        info.update(await _get_audio_info(file_path))
    
    return info


async def _calculate_file_hash(
    file_path: Path,
    algorithm: str = "md5"
) -> str:
    """
    Calculate file hash.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        str: File hash
    """
    hasher = hashlib.new(algorithm)
    
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()
