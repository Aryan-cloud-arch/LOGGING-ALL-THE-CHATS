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


async def _get_image_info(file_path: Path) -> Dict[str, Any]:
    """Get image-specific information."""
    try:
        with Image.open(file_path) as img:
            return {
                "type": "image",
                "format": img.format,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
                "resolution": f"{img.width}x{img.height}",
                "has_transparency": img.mode in ('RGBA', 'LA', 'P'),
                "is_animated": hasattr(img, 'is_animated') and img.is_animated
            }
    except Exception as e:
        logger.error(f"Failed to get image info: {e}")
        return {"type": "image", "error": str(e)}


async def _get_video_info(file_path: Path) -> Dict[str, Any]:
    """Get video-specific information."""
    try:
        probe = ffmpeg.probe(str(file_path))
        
        video_info = {"type": "video"}
        
        # Get video stream info
        video_streams = [
            s for s in probe['streams'] 
            if s['codec_type'] == 'video'
        ]
        
        if video_streams:
            stream = video_streams[0]
            video_info.update({
                "codec": stream.get('codec_name'),
                "width": stream.get('width'),
                "height": stream.get('height'),
                "resolution": f"{stream.get('width')}x{stream.get('height')}",
                "duration": float(probe['format'].get('duration', 0)),
                "fps": eval(stream.get('r_frame_rate', '0/1')),
                "bitrate": int(probe['format'].get('bit_rate', 0))
            })
        
        return video_info
        
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        return {"type": "video", "error": str(e)}


async def _get_audio_info(file_path: Path) -> Dict[str, Any]:
    """Get audio-specific information."""
    try:
        probe = ffmpeg.probe(str(file_path))
        
        audio_info = {"type": "audio"}
        
        # Get audio stream info
        audio_streams = [
            s for s in probe['streams'] 
            if s['codec_type'] == 'audio'
        ]
        
        if audio_streams:
            stream = audio_streams[0]
            audio_info.update({
                "codec": stream.get('codec_name'),
                "channels": stream.get('channels'),
                "sample_rate": stream.get('sample_rate'),
                "duration": float(probe['format'].get('duration', 0)),
                "bitrate": int(stream.get('bit_rate', 0))
            })
        
        return audio_info
        
    except Exception as e:
        logger.error(f"Failed to get audio info: {e}")
        return {"type": "audio", "error": str(e)}


# ==================== IMAGE OPTIMIZATION ====================

async def optimize_photo(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    max_size: Tuple[int, int] = (1920, 1080),
    quality: int = 85
) -> Optional[str]:
    """
    Optimize photo for size and quality.
    
    Args:
        input_path: Input image path
        output_path: Output path (optional, modifies in-place if None)
        max_size: Maximum dimensions (width, height)
        quality: JPEG quality (1-100)
        
    Returns:
        Optional[str]: Output path if successful
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path
        
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            # Resize if needed
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Auto-orient based on EXIF
            img = ImageOps.exif_transpose(img)
            
            # Save optimized
            img.save(
                output_path,
                format='JPEG',
                quality=quality,
                optimize=True
            )
        
        # Log size reduction
        original_size = input_path.stat().st_size
        new_size = output_path.stat().st_size
        
        if new_size < original_size:
            reduction = (1 - new_size / original_size) * 100
            logger.info(
                f"📸 Image optimized: {format_file_size(original_size)} → "
                f"{format_file_size(new_size)} ({reduction:.1f}% reduction)"
            )
        
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to optimize photo: {e}")
        return None


# ==================== VIDEO COMPRESSION ====================

async def compress_video(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    target_size_mb: Optional[int] = None,
    max_width: int = 1280,
    crf: int = 23
) -> Optional[str]:
    """
    Compress video file.
    
    Args:
        input_path: Input video path
        output_path: Output path (optional)
        target_size_mb: Target size in MB (optional)
        max_width: Maximum width
        crf: Constant Rate Factor (0-51, lower = better quality)
        
    Returns:
        Optional[str]: Output path if successful
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else \
                     input_path.with_suffix('.compressed.mp4')
        
        # Get input info
        probe = ffmpeg.probe(str(input_path))
        video_info = next(
            s for s in probe['streams'] 
            if s['codec_type'] == 'video'
        )
        
        width = int(video_info['width'])
        height = int(video_info['height'])
        
        # Calculate new dimensions
        if width > max_width:
            new_width = max_width
            new_height = int(height * (max_width / width))
            # Ensure even dimensions
            new_height = new_height - (new_height % 2)
        else:
            new_width = width
            new_height = height
        
        # Build ffmpeg command
        stream = ffmpeg.input(str(input_path))
        
        # Apply filters
        if new_width != width:
            stream = ffmpeg.filter(stream, 'scale', new_width, new_height)
        
        # Output settings
        stream = ffmpeg.output(
            stream,
            str(output_path),
            vcodec='libx264',
            crf=crf,
            preset='medium',
            acodec='aac',
            audio_bitrate='128k'
        )
        
        # Run compression
        await asyncio.create_subprocess_exec(
            *ffmpeg.compile(stream, overwrite_output=True),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        # Log compression
        original_size = input_path.stat().st_size
        new_size = output_path.stat().st_size
        
        if new_size < original_size:
            reduction = (1 - new_size / original_size) * 100
            logger.info(
                f"🎬 Video compressed: {format_file_size(original_size)} → "
                f"{format_file_size(new_size)} ({reduction:.1f}% reduction)"
            )
        
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to compress video: {e}")
        return None


# ==================== MEDIA PROCESSOR ====================

class MediaProcessor:
    """
    Advanced media processing pipeline.
    
    Features:
        - Automatic format detection
        - Batch processing
        - Progress tracking
        - Error recovery
    """
    
    def __init__(self, temp_dir: str = "temp"):
        """
        Initialize media processor.
        
        Args:
            temp_dir: Temporary directory for processing
        """
        self.temp_dir = ensure_directory(Path(temp_dir))
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._stats = {
            "processed": 0,
            "failed": 0,
            "total_size_saved": 0
        }
    
    async def process_media(
        self,
        file_path: Union[str, Path],
        optimize: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Process media file with auto-detection.
        
        Args:
            file_path: Media file path
            optimize: Whether to optimize/compress
            
        Returns:
            Optional[Dict]: Processing results
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # Get media info
        info = await get_media_info(file_path)
        
        if "error" in info:
            return info
        
        result = {
            "original": str(file_path),
            "info": info,
            "optimized": False,
            "output": str(file_path)
        }
        
        if not optimize:
            return result
        
        # Process based on type
        mime = info.get("mime_type", "")
        
        if mime.startswith("image/"):
            output = await optimize_photo(file_path)
            if output:
                result["optimized"] = True
                result["output"] = output
                
        elif mime.startswith("video/"):
            output = await compress_video(file_path)
            if output:
                result["optimized"] = True
                result["output"] = output
        
        return result
    
    async def batch_process(
        self,
        files: list[Union[str, Path]],
        optimize: bool = True,
        parallel: int = 3
    ) -> list[Dict[str, Any]]:
        """
        Process multiple media files.
        
        Args:
            files: List of file paths
            optimize: Whether to optimize
            parallel: Number of parallel processes
            
        Returns:
            List of processing results
        """
        semaphore = asyncio.Semaphore(parallel)
        
        async def process_one(file_path):
            async with semaphore:
                return await self.process_media(file_path, optimize)
        
        tasks = [process_one(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {files[i]}: {result}")
                self._stats["failed"] += 1
            else:
                processed.append(result)
                self._stats["processed"] += 1
        
        return processed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self._stats.copy()


# ==================== THUMBNAIL GENERATOR ====================

class ThumbnailGenerator:
    """
    Generate thumbnails for media files.
    
    Features:
        - Image thumbnails
        - Video thumbnails
        - Batch generation
        - Custom sizes
    """
    
    def __init__(
        self,
        thumb_size: Tuple[int, int] = (320, 320),
        video_position: float = 0.1
    ):
        """
        Initialize thumbnail generator.
        
        Args:
            thumb_size: Thumbnail dimensions
            video_position: Video position (0.0-1.0) for frame
        """
        self.thumb_size = thumb_size
        self.video_position = video_position
    
    async def generate(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None
    ) -> Optional[str]:
        """
        Generate thumbnail for media file.
        
        Args:
            input_path: Input media path
            output_path: Output thumbnail path
            
        Returns:
            Optional[str]: Thumbnail path if successful
        """
        input_path = Path(input_path)
        
        # Determine media type
        mime_type = mimetypes.guess_type(str(input_path))[0] or ""
        
        if mime_type.startswith("image/"):
            return await self._generate_image_thumb(input_path, output_path)
        elif mime_type.startswith("video/"):
            return await self._generate_video_thumb(input_path, output_path)
        
        logger.warning(f"Unsupported media type: {mime_type}")
        return None
    
    async def _generate_image_thumb(
        self,
        input_path: Path,
        output_path: Optional[Path]
    ) -> Optional[str]:
        """Generate thumbnail for image."""
        try:
            if not output_path:
                output_path = input_path.with_suffix('.thumb.jpg')
            
            with Image.open(input_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        rgb_img.paste(img, mask=img.split()[3])
                    else:
                        rgb_img.paste(img)
                    img = rgb_img
                
                # Generate thumbnail
                img.thumbnail(self.thumb_size, Image.Resampling.LANCZOS)
                
                # Save
                img.save(output_path, format='JPEG', quality=80)
            
            logger.debug(f"✅ Thumbnail generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate image thumbnail: {e}")
            return None
    
    async def _generate_video_thumb(
        self,
        input_path: Path,
        output_path: Optional[Path]
    ) -> Optional[str]:
        """Generate thumbnail for video."""
        try:
            if not output_path:
                output_path = input_path.with_suffix('.thumb.jpg')
            
            # Get video duration
            probe = ffmpeg.probe(str(input_path))
            duration = float(probe['format'].get('duration', 0))
            
            # Calculate timestamp for frame
            timestamp = duration * self.video_position
            
            # Extract frame
            stream = ffmpeg.input(str(input_path), ss=timestamp)
            stream = ffmpeg.filter(stream, 'scale', *self.thumb_size)
            stream = ffmpeg.output(
                stream,
                str(output_path),
                vframes=1,
                format='image2',
                vcodec='mjpeg'
            )
            
            # Run ffmpeg
            await asyncio.create_subprocess_exec(
                *ffmpeg.compile(stream, overwrite_output=True),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            logger.debug(f"✅ Video thumbnail generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate video thumbnail: {e}")
            return None
