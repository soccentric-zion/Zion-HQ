"""OIDC (human auth) client.

Talks to whatever issuer `settings.oidc_issuer` points at via standard
discovery (`/.well-known/openid-configuration`) + JWKS -- nothing here is
provider-specific, so swapping the dev Keycloak instance for a real IdP
later is a config change only (IMPLEMENTATION_PLAN §1.2).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from jose import jwt as jose_jwt

from app.config import get_settings


@dataclass(frozen=True)
class OIDCIdentity:
    subject: str
    email: str


class OIDCError(Exception):
    pass


class OIDCClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._discovery: dict | None = None
        self._jwks: dict | None = None
        self._jwks_fetched_at: float = 0.0

    async def _discover(self) -> dict:
        if self._discovery is None:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.settings.oidc_issuer}/.well-known/openid-configuration"
                )
                resp.raise_for_status()
                self._discovery = resp.json()
        return self._discovery

    async def _get_jwks(self) -> dict:
        # Cache for 5 minutes -- avoids hammering the IdP on every login
        # while still picking up key rotation reasonably promptly.
        if self._jwks is None or (time.monotonic() - self._jwks_fetched_at) > 300:
            disco = await self._discover()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(disco["jwks_uri"])
                resp.raise_for_status()
                self._jwks = resp.json()
                self._jwks_fetched_at = time.monotonic()
        return self._jwks

    def authorization_url(self, state: str, redirect_uri: str) -> str:
        client = AsyncOAuth2Client(
            client_id=self.settings.oidc_client_id,
            redirect_uri=redirect_uri,
            scope="openid email profile",
        )
        # authlib builds the URL synchronously against a known authorize
        # endpoint; discovery is only needed for token exchange/JWKS.
        authorize_endpoint = f"{self.settings.oidc_issuer}/protocol/openid-connect/auth"
        url, _ = client.create_authorization_url(authorize_endpoint, state=state)
        return url

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        # redirect_uri must exactly match what was sent to authorization_url
        # -- OAuth2 requires it (RFC 6749 §4.1.3), so callers must pass the
        # same value both times (see app/routers/auth.py's _redirect_uri()).
        disco = await self._discover()
        client = AsyncOAuth2Client(
            client_id=self.settings.oidc_client_id,
            client_secret=self.settings.oidc_client_secret,
            redirect_uri=redirect_uri,
        )
        token = await client.fetch_token(
            disco["token_endpoint"], code=code, grant_type="authorization_code"
        )
        return token

    async def verify_id_token(self, id_token: str, access_token: str) -> OIDCIdentity:
        jwks = await self._get_jwks()
        try:
            claims = jose_jwt.decode(
                id_token,
                jwks,
                algorithms=["RS256"],
                audience=self.settings.oidc_client_id,
                issuer=self.settings.oidc_issuer,
                # Keycloak's ID tokens carry at_hash (binds the ID token to
                # the access_token issued alongside it, OIDC core §3.1.3.6)
                # -- jose requires the access_token to verify it, else it
                # raises rather than silently skipping the check.
                access_token=access_token,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a uniform auth failure
            raise OIDCError(f"invalid id_token: {exc}") from exc

        email = claims.get("email")
        if not email:
            raise OIDCError("id_token missing email claim")
        return OIDCIdentity(subject=claims["sub"], email=email)
