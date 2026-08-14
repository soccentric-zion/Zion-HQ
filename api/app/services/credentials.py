"""Token generation/hashing shared by the REST API (mints pairing tokens,
rotates/revokes credentials) and agent-gateway (validates them on connect).

Single source of truth so the two independently-deployable services never
drift on hash algorithm or token format (IMPLEMENTATION_PLAN §2.2).
"""

import hashlib
import secrets


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
