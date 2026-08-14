from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AgentFrame(_message.Message):
    __slots__ = ("pairing_handshake", "heartbeat", "telemetry_batch", "fault_event", "log_upload_request", "command_ack")
    PAIRING_HANDSHAKE_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_BATCH_FIELD_NUMBER: _ClassVar[int]
    FAULT_EVENT_FIELD_NUMBER: _ClassVar[int]
    LOG_UPLOAD_REQUEST_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ACK_FIELD_NUMBER: _ClassVar[int]
    pairing_handshake: PairingHandshake
    heartbeat: Heartbeat
    telemetry_batch: TelemetryBatch
    fault_event: FaultEvent
    log_upload_request: LogUploadRequest
    command_ack: CommandAck
    def __init__(self, pairing_handshake: _Optional[_Union[PairingHandshake, _Mapping]] = ..., heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ..., telemetry_batch: _Optional[_Union[TelemetryBatch, _Mapping]] = ..., fault_event: _Optional[_Union[FaultEvent, _Mapping]] = ..., log_upload_request: _Optional[_Union[LogUploadRequest, _Mapping]] = ..., command_ack: _Optional[_Union[CommandAck, _Mapping]] = ...) -> None: ...

class PairingHandshake(_message.Message):
    __slots__ = ("pairing_token",)
    PAIRING_TOKEN_FIELD_NUMBER: _ClassVar[int]
    pairing_token: str
    def __init__(self, pairing_token: _Optional[str] = ...) -> None: ...

class Heartbeat(_message.Message):
    __slots__ = ("device_id", "credential_token", "sent_at_unix_ms", "agent_version")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SENT_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    AGENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    credential_token: str
    sent_at_unix_ms: int
    agent_version: str
    def __init__(self, device_id: _Optional[str] = ..., credential_token: _Optional[str] = ..., sent_at_unix_ms: _Optional[int] = ..., agent_version: _Optional[str] = ...) -> None: ...

class TelemetryBatch(_message.Message):
    __slots__ = ("samples", "location")
    SAMPLES_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    samples: _containers.RepeatedCompositeFieldContainer[TelemetrySample]
    location: Location
    def __init__(self, samples: _Optional[_Iterable[_Union[TelemetrySample, _Mapping]]] = ..., location: _Optional[_Union[Location, _Mapping]] = ...) -> None: ...

class TelemetrySample(_message.Message):
    __slots__ = ("metric", "value", "recorded_at_unix_ms", "tags")
    class TagsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    METRIC_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    metric: str
    value: float
    recorded_at_unix_ms: int
    tags: _containers.ScalarMap[str, str]
    def __init__(self, metric: _Optional[str] = ..., value: _Optional[float] = ..., recorded_at_unix_ms: _Optional[int] = ..., tags: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Location(_message.Message):
    __slots__ = ("lat", "lon", "accuracy_m", "source", "recorded_at_unix_ms")
    class Source(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[Location.Source]
        GNSS: _ClassVar[Location.Source]
        NETWORK: _ClassVar[Location.Source]
    UNKNOWN: Location.Source
    GNSS: Location.Source
    NETWORK: Location.Source
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    ACCURACY_M_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    accuracy_m: float
    source: Location.Source
    recorded_at_unix_ms: int
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ..., accuracy_m: _Optional[float] = ..., source: _Optional[_Union[Location.Source, str]] = ..., recorded_at_unix_ms: _Optional[int] = ...) -> None: ...

class FaultEvent(_message.Message):
    __slots__ = ("code", "severity", "message", "kind", "at_unix_ms", "fault_code_ref")
    class Severity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        INFO: _ClassVar[FaultEvent.Severity]
        WARN: _ClassVar[FaultEvent.Severity]
        CRITICAL: _ClassVar[FaultEvent.Severity]
    INFO: FaultEvent.Severity
    WARN: FaultEvent.Severity
    CRITICAL: FaultEvent.Severity
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RAISED: _ClassVar[FaultEvent.Kind]
        CLEARED: _ClassVar[FaultEvent.Kind]
    RAISED: FaultEvent.Kind
    CLEARED: FaultEvent.Kind
    CODE_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    FAULT_CODE_REF_FIELD_NUMBER: _ClassVar[int]
    code: str
    severity: FaultEvent.Severity
    message: str
    kind: FaultEvent.Kind
    at_unix_ms: int
    fault_code_ref: str
    def __init__(self, code: _Optional[str] = ..., severity: _Optional[_Union[FaultEvent.Severity, str]] = ..., message: _Optional[str] = ..., kind: _Optional[_Union[FaultEvent.Kind, str]] = ..., at_unix_ms: _Optional[int] = ..., fault_code_ref: _Optional[str] = ...) -> None: ...

class LogUploadRequest(_message.Message):
    __slots__ = ("kind", "time_range_start_unix_ms", "time_range_end_unix_ms", "size_bytes_estimate")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        LOG_BUNDLE: _ClassVar[LogUploadRequest.Kind]
        BACKUP: _ClassVar[LogUploadRequest.Kind]
    LOG_BUNDLE: LogUploadRequest.Kind
    BACKUP: LogUploadRequest.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    TIME_RANGE_START_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    TIME_RANGE_END_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_ESTIMATE_FIELD_NUMBER: _ClassVar[int]
    kind: LogUploadRequest.Kind
    time_range_start_unix_ms: int
    time_range_end_unix_ms: int
    size_bytes_estimate: int
    def __init__(self, kind: _Optional[_Union[LogUploadRequest.Kind, str]] = ..., time_range_start_unix_ms: _Optional[int] = ..., time_range_end_unix_ms: _Optional[int] = ..., size_bytes_estimate: _Optional[int] = ...) -> None: ...

class CommandAck(_message.Message):
    __slots__ = ("command_id", "success", "error")
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    command_id: str
    success: bool
    error: str
    def __init__(self, command_id: _Optional[str] = ..., success: _Optional[bool] = ..., error: _Optional[str] = ...) -> None: ...

class ServerFrame(_message.Message):
    __slots__ = ("pairing_result", "heartbeat_ack", "command", "signed_upload_url")
    PAIRING_RESULT_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_ACK_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    SIGNED_UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    pairing_result: PairingResult
    heartbeat_ack: HeartbeatAck
    command: Command
    signed_upload_url: SignedUploadUrl
    def __init__(self, pairing_result: _Optional[_Union[PairingResult, _Mapping]] = ..., heartbeat_ack: _Optional[_Union[HeartbeatAck, _Mapping]] = ..., command: _Optional[_Union[Command, _Mapping]] = ..., signed_upload_url: _Optional[_Union[SignedUploadUrl, _Mapping]] = ...) -> None: ...

class PairingResult(_message.Message):
    __slots__ = ("success", "error", "device_id", "credential_token")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TOKEN_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    device_id: str
    credential_token: str
    def __init__(self, success: _Optional[bool] = ..., error: _Optional[str] = ..., device_id: _Optional[str] = ..., credential_token: _Optional[str] = ...) -> None: ...

class HeartbeatAck(_message.Message):
    __slots__ = ("server_time_unix_ms", "next_heartbeat_interval_s")
    SERVER_TIME_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    NEXT_HEARTBEAT_INTERVAL_S_FIELD_NUMBER: _ClassVar[int]
    server_time_unix_ms: int
    next_heartbeat_interval_s: int
    def __init__(self, server_time_unix_ms: _Optional[int] = ..., next_heartbeat_interval_s: _Optional[int] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("command_id", "take_backup_now", "restore", "factory_reset", "apply_update")
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    TAKE_BACKUP_NOW_FIELD_NUMBER: _ClassVar[int]
    RESTORE_FIELD_NUMBER: _ClassVar[int]
    FACTORY_RESET_FIELD_NUMBER: _ClassVar[int]
    APPLY_UPDATE_FIELD_NUMBER: _ClassVar[int]
    command_id: str
    take_backup_now: TakeBackupNow
    restore: Restore
    factory_reset: FactoryReset
    apply_update: ApplyUpdate
    def __init__(self, command_id: _Optional[str] = ..., take_backup_now: _Optional[_Union[TakeBackupNow, _Mapping]] = ..., restore: _Optional[_Union[Restore, _Mapping]] = ..., factory_reset: _Optional[_Union[FactoryReset, _Mapping]] = ..., apply_update: _Optional[_Union[ApplyUpdate, _Mapping]] = ...) -> None: ...

class TakeBackupNow(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Restore(_message.Message):
    __slots__ = ("backup_download_url",)
    BACKUP_DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    backup_download_url: str
    def __init__(self, backup_download_url: _Optional[str] = ...) -> None: ...

class FactoryReset(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ApplyUpdate(_message.Message):
    __slots__ = ("artifact_id", "artifact_download_url", "checksum_sha256")
    ARTIFACT_ID_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_SHA256_FIELD_NUMBER: _ClassVar[int]
    artifact_id: str
    artifact_download_url: str
    checksum_sha256: str
    def __init__(self, artifact_id: _Optional[str] = ..., artifact_download_url: _Optional[str] = ..., checksum_sha256: _Optional[str] = ...) -> None: ...

class SignedUploadUrl(_message.Message):
    __slots__ = ("request_ref", "upload_url", "expires_at_unix_ms")
    REQUEST_REF_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    request_ref: str
    upload_url: str
    expires_at_unix_ms: int
    def __init__(self, request_ref: _Optional[str] = ..., upload_url: _Optional[str] = ..., expires_at_unix_ms: _Optional[int] = ...) -> None: ...
