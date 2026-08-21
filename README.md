# Zion-HQ

## Project Summary

Destructive workflows should remain behind an explicitly controlled test tenant and device.

Until the planning documents identify runnable services and repeatable checks, the feature rows are requirements inventory rather than acceptance results. This keeps cloud and device-side responsibilities distinguishable during implementation.

Zion-HQ is the planned cloud fleet-management application for Zion devices. The existing project description names the intended operator scope: viewing devices remotely, managing pairing and authorization, and running fleet operations such as telemetry, faults and alarms, logs, over-the-air updates, backup and restore, provisioning, factory reset, disable, and location. The repository tree adds `agent-gateway`, `api`, `infra`, `migrations`, `proto`, and `web` surfaces, plus Alembic configuration and a Makefile. Those names suggest service boundaries with an API, persistence migrations, protocol definitions, infrastructure, a web layer, and a gateway, but names alone are not enough to claim working workflows. The existing status is explicitly planning and points to `PLAN.md` and `ARCHITECTURE.md`, which should remain authoritative. This README preserves that caution while making the repository inventory visible. Feature rows therefore use `Unknown` or `Planned` where the scan cannot prove implementation, and test claims are limited to evidence that can be located. A useful first pass is to inspect the web and API manifests, read migration definitions, identify entry points, and run the Makefile checks. Cloud credentials, external services, device connectivity, authorization policy, OTA signing, and destructive operations require explicit setup and review. Zion-HQ is not the same component as Zion-Server: Server is the local orchestration/data plane, while HQ is intended to become the remote fleet-management plane.

## Feature Status

| # | Name / Description | Implemented? | Test Coverage? | Manual Test |
|---:|---|---|---|---|
| 1 | Repository layout for API, web, gateway, infra, proto, and migrations | Implemented | Tests not identified in top-level scan | [ ] Manual verification required |
| 2 | Remote device/fleet views | Planned | Not established | [ ] Manual verification required |
| 3 | Pairing and authorization management | Planned | Not established | [ ] Manual verification required |
| 4 | Telemetry collection and presentation | Planned | Not established | [ ] Manual verification required |
| 5 | Faults and alarms | Planned | Not established | [ ] Manual verification required |
| 6 | Remote log access | Planned | Not established | [ ] Manual verification required |
| 7 | OTA orchestration | Planned | Not established | [ ] Manual verification required |
| 8 | Backup and restore | Planned | Not established | [ ] Manual verification required |
| 9 | Provisioning and factory reset | Planned | Not established | [ ] Manual verification required |
| 10 | Disable and location operations | Planned | Not established | [ ] Manual verification required |
| 11 | Database migrations via Alembic configuration | Partial | Migration execution not verified | [ ] Manual verification required |
| 12 | Cloud deployment/infrastructure definitions | Partial | CI/deployment validation unknown | [ ] Manual verification required |

## Tests and Commands

```bash
cat PLAN.md ARCHITECTURE.md
make help
```

Use package-specific commands after inspecting the API and web manifests. No generic test command is claimed because the existing documentation does not provide one.

## Limitations

The project is explicitly planning-stage. No cloud deployment, API, web workflow, device connection, authorization policy, OTA, or destructive operation was verified.

## Detailed Reference

The retained planning overview below contains the original project-status links and scope statement.
# Zion-HQ

Cloud fleet-management app for Zion devices — view devices remotely, manage
pairing/authorization, and run fleet operations (telemetry, faults/alarms,
logs, OTA updates, backup/restore, provisioning, factory reset, disable,
location).

Status: **planning**. See [PLAN.md](PLAN.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
