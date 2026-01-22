"""
Messaging service for conversations and real-time communication.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessLogicException,
    InsufficientPermissionsException,
    NotFoundException,
)
from app.models.message import Conversation, Message, Notification
from app.models.user import User
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_or_create(
        self,
        user_one_id: UUID,
        user_two_id: UUID,
        property_id: UUID | None = None,
        booking_id: UUID | None = None,
    ) -> tuple[Conversation, bool]:
        """Get existing conversation or create new one."""
        # Check for existing conversation between users
        result = await self.session.execute(
            select(Conversation).where(
                or_(
                    and_(
                        Conversation.participant_one_id == user_one_id,
                        Conversation.participant_two_id == user_two_id,
                    ),
                    and_(
                        Conversation.participant_one_id == user_two_id,
                        Conversation.participant_two_id == user_one_id,
                    ),
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing, False

        # Create new conversation
        conversation = Conversation(
            participant_one_id=user_one_id,
            participant_two_id=user_two_id,
            property_id=property_id,
            booking_id=booking_id,
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation, True

    async def get_user_conversations(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get conversations for a user."""
        result = await self.session.execute(
            select(Conversation)
            .where(
                or_(
                    Conversation.participant_one_id == user_id,
                    Conversation.participant_two_id == user_id,
                )
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_last_message(
        self,
        conversation_id: UUID,
        message_preview: str,
        sender_id: UUID,
    ) -> None:
        """Update conversation with last message info."""
        conversation = await self.get(conversation_id)
        if not conversation:
            return

        conversation.last_message_at = datetime.now(UTC)
        conversation.last_message_preview = message_preview[:100]

        # Increment unread count for the other participant
        if conversation.participant_one_id == sender_id:
            conversation.unread_count_two += 1
        else:
            conversation.unread_count_one += 1

        await self.session.flush()


class MessageRepository(BaseRepository[Message]):
    """Repository for Message operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages in a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_as_read(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> int:
        """Mark all messages in conversation as read for user."""
        result = await self.session.execute(
            update(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.receiver_id == user_id,
                    Message.is_read == False,  # noqa: E712
                )
            )
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        await self.session.flush()
        return result.rowcount

    async def count_unread(self, user_id: UUID) -> int:
        """Count unread messages for a user."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(
                and_(
                    Message.receiver_id == user_id,
                    Message.is_read == False,  # noqa: E712
                )
            )
        )
        return result.scalar_one()


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)  # noqa: E712

        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self,
        notification_ids: list[UUID] | None,
        user_id: UUID,
    ) -> int:
        """Mark notifications as read."""
        query = update(Notification).where(Notification.user_id == user_id)

        if notification_ids:
            query = query.where(Notification.id.in_(notification_ids))

        result = await self.session.execute(
            query.values(is_read=True, read_at=datetime.now(UTC))
        )
        await self.session.flush()
        return result.rowcount

    async def count_unread(self, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
        )
        return result.scalar_one()


class MessagingService:
    """Service for messaging operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.notification_repo = NotificationRepository(session)

    # Conversations
    async def get_conversation(
        self, conversation_id: UUID, user: User
    ) -> Conversation:
        """Get conversation by ID with access check."""
        conversation = await self.conversation_repo.get(conversation_id)

        if not conversation:
            raise NotFoundException("Conversation")

        # Verify user is a participant
        if user.id not in [
            conversation.participant_one_id,
            conversation.participant_two_id,
        ]:
            raise InsufficientPermissionsException()

        return conversation

    async def start_conversation(
        self,
        sender: User,
        recipient_id: UUID,
        initial_message: str,
        property_id: UUID | None = None,
        booking_id: UUID | None = None,
    ) -> tuple[Conversation, Message]:
        """Start a new conversation or continue existing one."""
        if sender.id == recipient_id:
            raise BusinessLogicException(
                "Vous ne pouvez pas démarrer une conversation avec vous-même"
            )

        # Get or create conversation
        conversation, _ = await self.conversation_repo.get_or_create(
            user_one_id=sender.id,
            user_two_id=recipient_id,
            property_id=property_id,
            booking_id=booking_id,
        )

        # Send initial message
        message = await self.send_message(
            conversation_id=conversation.id,
            sender=sender,
            content=initial_message,
        )

        return conversation, message

    async def get_user_conversations(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """Get user's conversations with participant info."""
        conversations = await self.conversation_repo.get_user_conversations(
            user_id, skip=skip, limit=limit
        )

        result = []
        for conv in conversations:
            # Determine the other participant
            other_id = (
                conv.participant_two_id
                if conv.participant_one_id == user_id
                else conv.participant_one_id
            )

            # Get unread count for current user
            unread = (
                conv.unread_count_one
                if conv.participant_one_id == user_id
                else conv.unread_count_two
            )

            # Get other participant info
            other_user = await self.session.get(User, other_id)

            result.append({
                "id": conv.id,
                "other_participant": {
                    "id": other_user.id if other_user else None,
                    "first_name": other_user.first_name if other_user else "Utilisateur",
                    "last_name": other_user.last_name if other_user else "supprimé",
                    "avatar_url": other_user.avatar_url if other_user else None,
                    "is_verified": other_user.is_verified if other_user else False,
                },
                "property_id": conv.property_id,
                "last_message_at": conv.last_message_at,
                "last_message_preview": conv.last_message_preview,
                "unread_count": unread,
            })

        return result

    # Messages
    async def send_message(
        self,
        conversation_id: UUID,
        sender: User,
        content: str,
        attachments: list[dict] | None = None,
    ) -> Message:
        """Send a message in a conversation."""
        conversation = await self.get_conversation(conversation_id, sender)

        # Determine receiver
        receiver_id = (
            conversation.participant_two_id
            if conversation.participant_one_id == sender.id
            else conversation.participant_one_id
        )

        # Create message
        message = await self.message_repo.create({
            "conversation_id": conversation_id,
            "sender_id": sender.id,
            "receiver_id": receiver_id,
            "content": content,
            "attachments": attachments or [],
        })

        # Update conversation
        await self.conversation_repo.update_last_message(
            conversation_id=conversation_id,
            message_preview=content,
            sender_id=sender.id,
        )

        # Create notification for receiver
        await self.create_notification(
            user_id=receiver_id,
            notification_type="new_message",
            title="Nouveau message",
            body=f"{sender.first_name}: {content[:50]}...",
            data={
                "conversation_id": str(conversation_id),
                "message_id": str(message.id),
                "sender_id": str(sender.id),
            },
        )

        return message

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        user: User,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages in a conversation."""
        # Verify access
        await self.get_conversation(conversation_id, user)

        messages = await self.message_repo.get_conversation_messages(
            conversation_id, skip=skip, limit=limit
        )

        # Mark messages as read
        await self.mark_messages_read(conversation_id, user)

        return messages

    async def mark_messages_read(
        self, conversation_id: UUID, user: User
    ) -> int:
        """Mark messages as read."""
        count = await self.message_repo.mark_as_read(conversation_id, user.id)

        # Reset unread count in conversation
        conversation = await self.conversation_repo.get(conversation_id)
        if conversation:
            if conversation.participant_one_id == user.id:
                conversation.unread_count_one = 0
            else:
                conversation.unread_count_two = 0
            await self.session.flush()

        return count

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get total unread messages count."""
        return await self.message_repo.count_unread(user_id)

    # Notifications
    async def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> Notification:
        """Create a notification."""
        return await self.notification_repo.create({
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "body": body,
            "data": data or {},
        })

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """Get user's notifications."""
        return await self.notification_repo.get_user_notifications(
            user_id,
            unread_only=unread_only,
            skip=skip,
            limit=limit,
        )

    async def mark_notifications_read(
        self,
        user_id: UUID,
        notification_ids: list[UUID] | None = None,
    ) -> int:
        """Mark notifications as read."""
        return await self.notification_repo.mark_as_read(notification_ids, user_id)

    async def get_unread_notifications_count(self, user_id: UUID) -> int:
        """Get unread notifications count."""
        return await self.notification_repo.count_unread(user_id)
