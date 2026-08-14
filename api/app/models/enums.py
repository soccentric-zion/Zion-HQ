import enum


class UserRole(str, enum.Enum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"


class PairingState(str, enum.Enum):
    pending = "pending"
    authorized = "authorized"
    disabled = "disabled"
    revoked = "revoked"


class CredentialKind(str, enum.Enum):
    pairing = "pairing"
    long_lived = "long_lived"


class FaultSeverity(str, enum.Enum):
    info = "info"
    warn = "warn"
    critical = "critical"


class AlarmState(str, enum.Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"


class RolloutTarget(str, enum.Enum):
    all = "all"
    device_group = "device_group"
    specific_devices = "specific_devices"


class RolloutStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class DeviceRolloutStatus(str, enum.Enum):
    pending = "pending"
    applying = "applying"
    succeeded = "succeeded"
    failed = "failed"


class LogUploadKind(str, enum.Enum):
    log_bundle = "log_bundle"
    backup = "backup"


class CommandKind(str, enum.Enum):
    take_backup_now = "take_backup_now"
    restore = "restore"
    factory_reset = "factory_reset"
    apply_update = "apply_update"
