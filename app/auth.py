import os
from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UserDB

load_dotenv()
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
ALGORITHM = "HS256"

def secret_key():
    value = os.getenv("JWT_SECRET_KEY")
    if not value or len(value) < 32:
        raise RuntimeError("JWT_SECRET_KEY missing or too short in .env")
    return value

def create_access_token(user_id: int):
    minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=minutes)}, secret_key(), algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserDB:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的登录凭证", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, secret_key(), algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise error
    user = db.get(UserDB, user_id)
    if user is None or user.username.startswith("__legacy_archive__"):
        raise error
    return user
