import time
import uuid

from jose import JWTError, jwt

from app.config import get_settings


class InvalidSession(Exception):
    pass


def issue_session_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "iat": now,
        "exp": now + settings.session_ttl_seconds,
    }
    return jwt.encode(claims, settings.session_secret_key, algorithm=settings.session_algorithm)


def verify_session_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.session_secret_key, algorithms=[settings.session_algorithm]
        )
    except JWTError as exc:
        raise InvalidSession(str(exc)) from exc
