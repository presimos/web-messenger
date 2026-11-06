import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from pwdlib import PasswordHash

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(username: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def get_token_subject(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
