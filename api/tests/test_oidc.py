"""Regression test for a real bug found during manual LAN testing: Keycloak's
ID tokens carry an `at_hash` claim (binds the ID token to the access_token
per OIDC core §3.1.3.6), and jose.jwt.decode raises unless the access_token
is passed in to verify it -- see app/auth/oidc.py::verify_id_token.
"""

import base64
import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.auth.oidc import OIDCClient, OIDCError

ISSUER = "http://keycloak.test/realms/zionhq"
CLIENT_ID = "zionhq-api"
KID = "test-key-1"


def _b64url_uint(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()


@pytest.fixture
def rsa_jwk() -> dict:
    """A JWK (with private parts, for signing) that jose can also use as a
    JWKS entry for verification -- mirrors what OIDCClient._get_jwks()
    would fetch, minus the network call."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.private_numbers()
    public_numbers = numbers.public_numbers
    # n/e/d alone is sufficient for jose to sign -- RFC7518 §6.3.2 requires
    # dp/dq/qi too if p/q are present at all, which we don't need here.
    return {
        "kty": "RSA",
        "kid": KID,
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
        "d": _b64url_uint(numbers.d),
    }


@pytest.fixture
def signed_tokens(rsa_jwk):
    access_token = "opaque-access-token-value"
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "user-123",
        "email": "admin@example.com",
        "exp": int(time.time()) + 300,
        "iat": int(time.time()),
    }
    id_token = jose_jwt.encode(
        claims, rsa_jwk, algorithm="RS256", access_token=access_token, headers={"kid": KID}
    )
    return id_token, access_token


def _client_with_key(rsa_jwk) -> OIDCClient:
    client = OIDCClient()
    client.settings.oidc_issuer = ISSUER
    client.settings.oidc_client_id = CLIENT_ID
    # Public-only view, same shape _get_jwks() would return from the IdP.
    public_jwk = {k: v for k, v in rsa_jwk.items() if k not in ("d", "p", "q")}
    client._jwks = {"keys": [public_jwk]}
    client._jwks_fetched_at = time.monotonic()
    return client


async def test_verify_id_token_succeeds_with_at_hash_when_access_token_given(
    rsa_jwk, signed_tokens
):
    id_token, access_token = signed_tokens
    client = _client_with_key(rsa_jwk)

    identity = await client.verify_id_token(id_token, access_token)
    assert identity.email == "admin@example.com"
    assert identity.subject == "user-123"


async def test_verify_id_token_fails_with_wrong_access_token(rsa_jwk, signed_tokens):
    id_token, _access_token = signed_tokens
    client = _client_with_key(rsa_jwk)

    with pytest.raises(OIDCError):
        await client.verify_id_token(id_token, "a-different-access-token")
