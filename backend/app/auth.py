from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.security import create_access_token, get_token_subject, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Имя пользователя уже занято")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверное имя пользователя или пароль")
    return TokenResponse(access_token=create_access_token(user.username))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется действующий токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    username = get_token_subject(credentials.credentials)
    if username is None:
        raise unauthorized
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise unauthorized
    return user


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user
