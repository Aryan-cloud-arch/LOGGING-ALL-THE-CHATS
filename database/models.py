"""
Database Models
===============
Pydantic models for data validation and serialization.
Ensures data consistency and type safety.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


class SenderType(str, Enum):
    """Message sender enumeration."""
    YOU = "you"
    HER = "her"
    SYSTEM = "system"


class MediaType(str, Enum):
    """Media type enumeration."""
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"
    STICKER = "sticker"
    GIF = "gif"
    AUDIO = "audio"
    CONTACT = "contact"
    LOCATION = "location"
    POLL = "poll"
    NONE = "none"


class MessageModel(BaseModel):
    """
    Message model for database storage.
    
    Attributes:
        original_id: Message ID in original DM chat
        group_id: Message ID in backup group
        sender: Who sent the message
        content: Text content or caption
        timestamp: When message was sent
        has_media: Whether message contains media
        media_type: Type of media if present
        media_path: Path to saved media (for view-once)
        reply_to_original: Original message ID being replied to
        reply_to_group: Group message ID being replied to
        is_forwarded: Whether message is forwarded
        is_edited: Whether message has been edited
        is_deleted: Whether message has been deleted
        view_once: Whether media was view-once
        metadata: Additional message metadata
    """
    
    # Primary identifiers
    original_id: int = Field(..., description="Message ID in DM")
    group_id: int = Field(..., description="Message ID in group")
    
    # Sender information
    sender: SenderType = Field(..., description="Message sender")
    
    # Content
    content: Optional[str] = Field(None, description="Text content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Media information
    has_media: bool = Field(False, description="Has media attachment")
    media_type: MediaType = Field(MediaType.NONE, description="Type of media")
    media_path: Optional[str] = Field(None, description="Saved media path")
    
    # Reply chain
    reply_to_original: Optional[int] = Field(None, description="Reply to ID in DM")
    reply_to_group: Optional[int] = Field(None, description="Reply to ID in group")
    
    # Status flags
    is_forwarded: bool = Field(False, description="Is forwarded message")
    is_edited: bool = Field(False, description="Has been edited")
    is_deleted: bool = Field(False, description="Has been deleted")
    view_once: bool = Field(False, description="Was view-once media")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('content')
    def truncate_content(cls, v):
        """Truncate very long content for storage efficiency."""
        if v and len(v) > 4096:  # Telegram max message length
            return v[:4093] + "..."
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB."""
        data = self.dict()
        data['timestamp'] = self.timestamp
        return data


class EditHistoryModel(BaseModel):
    """
    Edit history tracking model.
    
    Tracks all edits made to a message.
    """
    
    original_id: int = Field(..., description="Original message ID")
    edit_time: datetime = Field(default_factory=datetime.utcnow)
    old_content: str = Field(..., description="Content before edit")
    new_content: str = Field(..., description="Content after edit")
    edit_notification_id: Optional[int] = Field(None, description="Edit notification message ID")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReplyChainModel(BaseModel):
    """
    Reply chain relationship model.
    
    Maps reply relationships between original and group messages.
    """
    
    # Original chat IDs
    original_id: int = Field(..., description="Message ID in DM")
    original_reply_to: int = Field(..., description="Reply to ID in DM")
    
    # Group chat IDs
    group_id: int = Field(..., description="Message ID in group")
    group_reply_to: int = Field(..., description="Reply to ID in group")
    
    # Chain metadata
    chain_depth: int = Field(1, description="Depth in reply chain")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SystemStateModel(BaseModel):
    """
    System state tracking model.
    
    Stores system state for recovery and monitoring.
    """
    
    key: str = Field(..., description="State key")
    value: Any = Field(..., description="State value")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CollectionStats(BaseModel):
    """Database collection statistics."""
    
    total_messages: int = 0
    total_edits: int = 0
    total_deletes: int = 0
    total_media: int = 0
    total_view_once: int = 0
    messages_today: int = 0
    storage_size_mb: float = 0.0
    last_message_time: Optional[datetime] = None
