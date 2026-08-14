from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZIONHQ_", env_file=".env", extra="ignore")

    env: str = "dev"

    database_url: str = "postgresql+asyncpg://zionhq:zionhq@localhost:5432/zionhq"

    # OIDC (human auth). Dev default points at the self-hosted Keycloak
    # brought up by infra/docker-compose.yml -- see IMPLEMENTATION_PLAN §1.2:
    # "if no IdP is chosen yet, use a self-hosted option... so Phase 1 isn't
    # blocked on an external vendor decision."
    oidc_issuer: str = "http://localhost:8081/realms/zionhq"
    oidc_client_id: str = "zionhq-api"
    oidc_client_secret: str = "dev-secret-change-me"
    # No static oidc_redirect_uri: it's derived per-request from the
    # browser's actual origin (X-Forwarded-Host, forwarded by Vite's dev
    # proxy) in app/routers/auth.py -- a fixed value breaks the moment the
    # app is reachable at more than one hostname (localhost, LAN IP, mDNS
    # name), which is exactly what the LAN-access setup needs.
    oidc_redirect_fallback_host: str = "localhost:5173"

    # Session JWT issued by the API after OIDC login, stored in an httpOnly cookie.
    session_secret_key: str = "dev-only-change-me-in-every-real-deployment"
    session_algorithm: str = "HS256"
    session_ttl_seconds: int = 60 * 60 * 8

    # Object storage (S3-compatible; MinIO in local dev).
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "zionhq"
    s3_secret_key: str = "zionhq-dev-secret"
    s3_bucket: str = "zionhq"
    s3_region: str = "us-east-1"

    # Redis (arq background jobs).
    redis_url: str = "redis://localhost:6379/0"

    # Presence / heartbeat.
    heartbeat_interval_s: int = 30
    heartbeat_missed_threshold: int = 2  # offline after N missed intervals

    # Pairing tokens.
    pairing_token_ttl_seconds: int = 15 * 60

    cors_allow_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
