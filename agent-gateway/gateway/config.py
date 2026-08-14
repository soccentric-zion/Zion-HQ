from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZIONHQ_GATEWAY_", extra="ignore")

    grpc_port: int = 50051
    # Stale-connection sweep cadence -- independent of the heartbeat interval
    # itself (app.config.Settings.heartbeat_interval_s), which devices use to
    # decide how often to send heartbeats.
    sweep_interval_s: int = 10


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()
