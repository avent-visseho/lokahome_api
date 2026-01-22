"""
Message models for user communication.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Conversation(BaseModel):
    """Conversation between two users."""

    __tablename__ = "conversations"

    # Participants
    participant_one_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    participant_two_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Optional property reference
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL")
    )

    # Optional booking reference
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )

    # Last message preview
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_preview: Mapped[str | None] = mapped_column(String(100))

    # Unread counts
    unread_count_one: Mapped[int] = mapped_column(default=0, nullable=False)
    unread_count_two: Mapped[int] = mapped_column(default=0, nullable=False)

    # Status
    is_archived_one: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_archived_two: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id}>"


class Message(BaseModel):
    """Individual message within a conversation."""

    __tablename__ = "messages"

    # Conversation reference
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Sender and receiver
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Attachments (images, documents)
    attachments: Mapped[list | None] = mapped_column(
        JSONB, default=[]
    )  # [{"type": "image", "url": "..."}]

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Soft delete
    deleted_by_sender: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    deleted_by_receiver: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    sender: Mapped["User"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_messages"
    )
    receiver: Mapped["User"] = relationship(
        "User", foreign_keys=[receiver_id], back_populates="received_messages"
    )

    def __repr__(self) -> str:
        return f"<Message {self.id}>"


class Notification(BaseModel):
    """User notifications."""

    __tablename__ = "notifications"

    # User reference
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Notification type
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # booking_confirmed, new_message, etc.

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Reference data
    data: Mapped[dict | None] = mapped_column(
        JSONB, default={}
    )  # {"booking_id": "...", "property_id": "..."}

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Delivery status
    sent_push: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Notification {self.id}>"
