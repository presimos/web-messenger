import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal, get_db
from app.models import Chat, ChatMember, Message, User, utc_now
from app.schemas import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from app.security import get_token_subject

router = APIRouter(tags=["messaging"])
websocket_router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, chat_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[chat_id].add(websocket)

    def disconnect(self, chat_id: int, websocket: WebSocket) -> None:
        connections = self.connections.get(chat_id)
        if connections is not None:
            connections.discard(websocket)
            if not connections:
                self.connections.pop(chat_id, None)

    async def broadcast(self, chat_id: int, payload: dict) -> None:
        for connection in list(self.connections.get(chat_id, ())):
            try:
                await connection.send_json(payload)
            except WebSocketDisconnect:
                self.disconnect(chat_id, connection)


manager = ConnectionManager()


def require_membership(db: Session, chat_id: int, user_id: int) -> Chat:
    chat = db.scalar(
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(Chat.id == chat_id, ChatMember.user_id == user_id)
    )
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    return chat


@router.post("/chats", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Chat:
    names = list(dict.fromkeys([current_user.username, *payload.member_usernames]))
    users = list(db.scalars(select(User).where(User.username.in_(names))))
    if len(users) != len(names):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Один или несколько пользователей не найдены")

    chat = Chat(title=payload.title)
    db.add(chat)
    db.flush()
    db.add_all(ChatMember(chat_id=chat.id, user_id=user.id) for user in users)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/chats", response_model=list[ChatResponse])
def list_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Chat]:
    return list(
        db.scalars(
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == current_user.id)
            .order_by(Chat.created_at.desc(), Chat.id.desc())
        )
    )


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
def list_messages(
    chat_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    require_membership(db, chat_id, current_user.id)
    rows = db.execute(
        select(Message, User.username)
        .join(User, User.id == Message.sender_id)
        .where(Message.chat_id == chat_id)
        .order_by(Message.id.desc())
        .limit(limit)
    ).all()
    return [
        MessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=message.sender_id,
            sender_username=username,
            body=message.body,
            created_at=message.created_at,
        )
        for message, username in reversed(rows)
    ]


@websocket_router.websocket("/ws/chats/{chat_id}")
async def chat_socket(websocket: WebSocket, chat_id: int) -> None:
    token = websocket.query_params.get("token", "")
    username = get_token_subject(token)
    if username is None:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username))
        membership = db.scalar(
            select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == getattr(user, "id", None))
        )
        if user is None or membership is None:
            await websocket.close(code=4403)
            return
        await manager.connect(chat_id, websocket)
        while True:
            raw_payload = await websocket.receive_text()
            try:
                payload = MessageCreate.model_validate_json(raw_payload)
            except (ValidationError, ValueError):
                await websocket.send_json({"error": "Передано неверное сообщение"})
                continue

            message = Message(
                chat_id=chat_id,
                sender_id=user.id,
                body=payload.body,
                created_at=utc_now(),
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            await manager.broadcast(
                chat_id,
                MessageResponse(
                    id=message.id,
                    chat_id=message.chat_id,
                    sender_id=message.sender_id,
                    sender_username=user.username,
                    body=message.body,
                    created_at=message.created_at,
                ).model_dump(mode="json"),
            )
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(chat_id, websocket)
        db.close()
