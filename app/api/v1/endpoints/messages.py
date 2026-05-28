"""
Messaging endpoints for conversations, messages, and notifications.
Includes WebSocket support for real-time communication.
"""
import uuid as uuid_mod
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, WebSocket, WebSocketDisconnect, status

from app.api.deps import ActiveUser, DbSession
from app.core.security import decode_token
from app.schemas.base import MessageResponse
from app.schemas.message import (
    ChatMessageResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MarkNotificationsRead,
    MessageCreate,
    MessageListResponse,
    NotificationListResponse,
    ReplyToMessageResponse,
)
from app.services.messaging import MessagingService

router = APIRouter(prefix="/messages", tags=["Messages"])

# Upload configuration
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent.parent / "static" / "uploads" / "messages"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
ALLOWED_DOC_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ALL_ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_DOC_TYPES
MAX_IMAGE_DOC_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB


# === File Upload ===

@router.post(
    "/upload",
    summary="Uploader un fichier pour le chat",
)
async def upload_chat_file(
    current_user: ActiveUser,
    file: UploadFile = File(...),
):
    """
    Uploader un fichier à joindre à un message.

    - Images : JPEG, PNG, WebP, GIF (max 10 Mo)
    - Vidéos : MP4, MOV, AVI (max 50 Mo)
    - Documents : PDF, DOC, DOCX, XLS, XLSX (max 10 Mo)
    """
    from fastapi import HTTPException

    content_type = file.content_type or ""
    if content_type not in ALL_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Type de fichier non autorisé.",
        )

    contents = await file.read()
    max_size = MAX_VIDEO_SIZE if content_type in ALLOWED_VIDEO_TYPES else MAX_IMAGE_DOC_SIZE
    if len(contents) > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Le fichier ne doit pas dépasser {limit_mb} Mo.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    original_name = file.filename or "file"
    ext = Path(original_name).suffix.lower()
    filename = f"{uuid_mod.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(contents)

    url = f"/static/uploads/messages/{filename}"
    return {
        "url": url,
        "name": original_name,
        "size": len(contents),
        "mime_type": content_type,
    }


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


def _build_reply_to(message) -> ReplyToMessageResponse | None:
    """Build a ReplyToMessageResponse from a message's reply_to relationship."""
    if message.reply_to_id is None or message.reply_to is None:
        return None
    parent = message.reply_to
    return ReplyToMessageResponse(
        id=parent.id,
        sender_id=parent.sender_id,
        content=parent.content[:100],
    )


def _build_message_response(message) -> ChatMessageResponse:
    """Build a ChatMessageResponse with reply_to data."""
    return ChatMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        content=message.content,
        attachments=message.attachments,
        reply_to_id=message.reply_to_id,
        reply_to=_build_reply_to(message),
        is_read=message.is_read,
        read_at=message.read_at,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _build_message_list_response(message) -> MessageListResponse:
    """Build a MessageListResponse with reply_to data."""
    return MessageListResponse(
        id=message.id,
        sender_id=message.sender_id,
        content=message.content,
        attachments=message.attachments,
        reply_to_id=message.reply_to_id,
        reply_to=_build_reply_to(message),
        is_read=message.is_read,
        created_at=message.created_at,
    )


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
    conversation, message, is_new = await service.start_conversation(
        sender=current_user,
        recipient_id=data.participant_id,
        initial_message=data.initial_message,
        property_id=data.property_id,
        booking_id=data.booking_id,
        attachments=data.attachments,
    )

    # Refresh conversation after send_message flushes expired its attributes
    await session.refresh(conversation)

    # Notify recipient via WebSocket only if a message was sent
    if message is not None:
        await manager.send_personal_message(
            {
                "type": "new_conversation",
                "conversation_id": str(conversation.id),
                "message": {
                    "id": str(message.id),
                    "content": message.content,
                    "sender_id": str(current_user.id),
                    "attachments": message.attachments,
                    "created_at": message.created_at.isoformat(),
                },
            },
            str(data.participant_id),
        )

    # Compute unread_count for current user
    unread = (
        conversation.unread_count_one
        if conversation.participant_one_id == current_user.id
        else conversation.unread_count_two
    )
    return ConversationResponse(
        id=conversation.id,
        participant_one_id=conversation.participant_one_id,
        participant_two_id=conversation.participant_two_id,
        property_id=conversation.property_id,
        booking_id=conversation.booking_id,
        last_message_at=conversation.last_message_at,
        last_message_preview=conversation.last_message_preview,
        unread_count=unread,
        is_new=is_new,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


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
    conversation = await service.get_conversation(conversation_id, current_user)

    # Compute unread_count for current user
    unread = (
        conversation.unread_count_one
        if conversation.participant_one_id == current_user.id
        else conversation.unread_count_two
    )
    return ConversationResponse(
        id=conversation.id,
        participant_one_id=conversation.participant_one_id,
        participant_two_id=conversation.participant_two_id,
        property_id=conversation.property_id,
        booking_id=conversation.booking_id,
        last_message_at=conversation.last_message_at,
        last_message_preview=conversation.last_message_preview,
        unread_count=unread,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


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
    messages = await service.get_conversation_messages(
        conversation_id=conversation_id,
        user=current_user,
        skip=skip,
        limit=limit,
    )
    return [_build_message_list_response(m) for m in messages]


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
        reply_to_id=data.reply_to_id,
    )

    # Refresh message after multiple flushes expired its attributes
    await session.refresh(message)

    # Notify recipient via WebSocket
    ws_payload: dict = {
        "id": str(message.id),
        "content": message.content,
        "sender_id": str(current_user.id),
        "attachments": message.attachments,
        "reply_to_id": str(message.reply_to_id) if message.reply_to_id else None,
        "created_at": message.created_at.isoformat(),
    }
    await manager.send_personal_message(
        {
            "type": "message",
            "conversation_id": str(conversation_id),
            "message": ws_payload,
        },
        str(recipient_id),
    )

    return _build_message_response(message)


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
