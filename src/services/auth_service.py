import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set. Check your .env file.")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _prepare_password(password: str) -> str:
    """Bcrypt only ever uses the first 72 BYTES of a password (a property of
    the algorithm itself, not a choice we're making). We truncate explicitly
    here so behavior is predictable rather than relying on the library to
    error or silently truncate for us. Truncating by bytes (not characters)
    matters because multi-byte UTF-8 characters can push a short-looking
    string over the limit."""
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(_prepare_password(plain_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(_prepare_password(plain_password), hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
