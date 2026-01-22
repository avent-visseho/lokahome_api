"""
Messaging endpoints for conversations, messages, and notifications.
Includes WebSocket support for real-time communication.
"""
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.deps import ActiveUser, DbSession
from app.core.security import decode_token
from app.schemas.base import MessageResponse
from app.schemas.message import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MarkNotificationsRead,
    MessageCreate,
    MessageListResponse,
    NotificationListResponse,
)
from app.schemas.message import ChatMessageResponse
from app.services.messaging import MessagingService

router = APIRouter(prefix="/messages", tags=["Messages"])


# === WebSocket Connection Manager ===

class ConnectionManager:
    """Manages WebSocket connections for real-time messaging."""

    def __init__(self):
        # user_id -> list of WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user's WebSocket."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a user's WebSocket."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to a specific user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def broadcast_to_conversation(
        self, message: dict, user_ids: list[str]
    ):
        """Send message to all participants in a conversation."""
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)


# Global connection manager
manager = ConnectionManager()


# === WebSocket Endpoint ===

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
):
    """
    WebSocket endpoint for real-time messaging.

    Connect with: ws://host/api/v1/messages/ws?token=<jwt_token>

    Message types:
    - message: New chat message
    - typing: User is typing indicator
    - read: Message read receipt
    """
    # Verify token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "typing":
                # Broadcast typing indicator
                conversation_id = data.get("conversation_id")
                await manager.broadcast_to_conversation(
                    {
                        "type": "typing",
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "is_typing": data.get("is_typing", True),
                    },
                    [data.get("recipient_id", "")],
                )

            elif message_type == "read":
                # Broadcast read receipt
                await manager.broadcast_to_conversation(
                    {
                        "type": "read",
                        "user_id": user_id,
                        "conversation_id": data.get("conversation_id"),
                        "message_ids": data.get("message_ids", []),
                    },
                    [data.get("sender_id", "")],
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# === Conversations ===

@router.get(
    "/conversations",
    response_model=list[ConversationListResponse],
    summary="Mes conversations",
)
async def get_conversations(
    current_user: ActiveUser,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer la liste de mes conversations."""
    service = MessagingService(session)
    return await service.get_user_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Démarrer une conversation",
)
async def start_conversation(
    data: ConversationCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Démarrer une nouvelle conversation ou continuer une existante.

    - **participant_id**: ID de l'utilisateur destinataire
    - **initial_message**: Premier message de la conversation
    - **property_id**: (Optionnel) ID du bien concerné
    """
    service = MessagingService(session)
    conversation, message = await service.start_conversation(
        sender=current_user,
        recipient_id=data.participant_id,
        initial_message=data.initial_message,
        property_id=data.property_id,
        booking_id=data.booking_id,
    )

    # Notify recipient via WebSocket
    await manager.send_personal_message(
        {
            "type": "new_conversation",
            "conversation_id": str(conversation.id),
            "message": {
                "id": str(message.id),
                "content": message.content,
                "sender_id": str(current_user.id),
                "created_at": message.created_at.isoformat(),
            },
        },
        str(data.participant_id),
    )

    return conversation


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Détails d'une conversation",
)
async def get_conversation(
    conversation_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Récupérer les détails d'une conversation."""
    service = MessagingService(session)
    return await service.get_conversation(conversation_id, current_user)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageListResponse],
    summary="Messages d'une conversation",
)
async def get_conversation_messages(
    conversation_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer les messages d'une conversation."""
    service = MessagingService(session)
    return await service.get_conversation_messages(
        conversation_id=conversation_id,
        user=current_user,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer un message",
)
async def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: ActiveUser,
    session: DbSession,
):
    """Envoyer un message dans une conversation."""
    service = MessagingService(session)

    # Get conversation to find recipient
    conversation = await service.get_conversation(conversation_id, current_user)
    recipient_id = (
        conversation.participant_two_id
        if conversation.participant_one_id == current_user.id
        else conversation.participant_one_id
    )

    message = await service.send_message(
        conversation_id=conversation_id,
        sender=current_user,
        content=data.content,
        attachments=data.attachments,
    )

    # Notify recipient via WebSocket
    await manager.send_personal_message(
        {
            "type": "message",
            "conversation_id": str(conversation_id),
            "message": {
                "id": str(message.id),
                "content": message.content,
                "sender_id": str(current_user.id),
                "attachments": message.attachments,
                "created_at": message.created_at.isoformat(),
            },
        },
        str(recipient_id),
    )

    return message


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=MessageResponse,
    summary="Marquer comme lu",
)
async def mark_conversation_read(
    conversation_id: UUID,
    current_user: ActiveUser,
    session: DbSession,
):
    """Marquer tous les messages d'une conversation comme lus."""
    service = MessagingService(session)
    count = await service.mark_messages_read(conversation_id, current_user)
    return MessageResponse(message=f"{count} message(s) marqué(s) comme lu(s)")


@router.get(
    "/unread-count",
    summary="Nombre de messages non lus",
)
async def get_unread_count(
    current_user: ActiveUser,
    session: DbSession,
):
    """Obtenir le nombre total de messages non lus."""
    service = MessagingService(session)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


# === Notifications ===

@router.get(
    "/notifications",
    response_model=list[NotificationListResponse],
    summary="Mes notifications",
)
async def get_notifications(
    current_user: ActiveUser,
    session: DbSession,
    unread_only: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Récupérer mes notifications."""
    service = MessagingService(session)
    return await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/notifications/read",
    response_model=MessageResponse,
    summary="Marquer les notifications comme lues",
)
async def mark_notifications_read(
    data: MarkNotificationsRead,
    current_user: ActiveUser,
    session: DbSession,
):
    """
    Marquer des notifications comme lues.

    - Sans IDs spécifiques: marque toutes comme lues
    - Avec IDs: marque uniquement celles spécifiées
    """
    service = MessagingService(session)
    count = await service.mark_notifications_read(
        user_id=current_user.id,
        notification_ids=data.notification_ids,
    )
    return MessageResponse(message=f"{count} notification(s) marquée(s) comme lue(s)")


@router.get(
    "/notifications/unread-count",
    summary="Nombre de notifications non lues",
)
async def get_unread_notifications_count(
    current_user: ActiveUser,
    session: DbSession,
):
    """Obtenir le nombre de notifications non lues."""
    service = MessagingService(session)
    count = await service.get_unread_notifications_count(current_user.id)
    return {"unread_count": count}
