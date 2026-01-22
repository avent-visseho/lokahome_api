"""
Message and notification schemas for validation and serialization.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDSchema, TimestampSchema
from app.schemas.user import UserPublicProfile


# --- Conversation Schemas ---
class ConversationCreate(BaseSchema):
    """Create a new conversation."""

    participant_id: UUID
    property_id: UUID | None = None
    booking_id: UUID | None = None
    initial_message: str = Field(min_length=1)


class ConversationResponse(IDSchema, TimestampSchema):
    """Conversation response schema."""

    participant_one_id: UUID
    participant_two_id: UUID
    property_id: UUID | None
    booking_id: UUID | None
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int  # For current user


class ConversationListResponse(BaseSchema):
    """Conversation list item."""

    id: UUID
    other_participant: UserPublicProfile
    property_id: UUID | None
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int


# --- Message Schemas ---
class MessageCreate(BaseSchema):
    """Create a new message."""

    content: str = Field(min_length=1)
    attachments: list[dict] | None = None  # [{"type": "image", "url": "..."}]


class ChatMessageResponse(IDSchema, TimestampSchema):
    """Chat message response schema."""

    conversation_id: UUID
    sender_id: UUID
    receiver_id: UUID
    content: str
    attachments: list[dict] | None
    is_read: bool
    read_at: datetime | None


class MessageListResponse(BaseSchema):
    """Message list item."""

    id: UUID
    sender_id: UUID
    content: str
    attachments: list[dict] | None
    is_read: bool
    created_at: datetime


# --- Notification Schemas ---
class NotificationResponse(IDSchema, TimestampSchema):
    """Notification response schema."""

    type: str
    title: str
    body: str
    data: dict | None
    is_read: bool
    read_at: datetime | None


class NotificationListResponse(BaseSchema):
    """Notification list item."""

    id: UUID
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class MarkNotificationsRead(BaseSchema):
    """Mark notifications as read request."""

    notification_ids: list[UUID] | None = None  # None = mark all as read


class NotificationPreferences(BaseSchema):
    """User notification preferences."""

    email: bool = True
    push: bool = True
    sms: bool = False

    # Granular preferences
    booking_updates: bool = True
    new_messages: bool = True
    payment_updates: bool = True
    promotional: bool = False


# --- WebSocket Schemas ---
class WebSocketMessage(BaseSchema):
    """WebSocket message format."""

    type: str  # "message", "typing", "read"
    data: dict


class TypingIndicator(BaseSchema):
    """Typing indicator payload."""

    conversation_id: UUID
    is_typing: bool


class MessageReadReceipt(BaseSchema):
    """Message read receipt payload."""

    conversation_id: UUID
    message_ids: list[UUID]
