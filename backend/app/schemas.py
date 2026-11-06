from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Имя пользователя не может быть пустым")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatCreate(BaseModel):
    title: str = Field(default="Новый чат", min_length=1, max_length=100)
    member_usernames: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название чата не может быть пустым")
        return value

    @field_validator("member_usernames")
    @classmethod
    def normalize_usernames(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip().lower() for value in values if value.strip()))


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Сообщение не может быть пустым")
        return value


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    sender_username: str
    body: str
    created_at: datetime
