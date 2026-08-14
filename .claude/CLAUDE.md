# Zion-HQ

Cloud fleet-management app: API, database and browser UI. An operator sees every paired device's
status remotely and runs operations against it. The only cloud-hosted leaf.

## How you work here

* Commands: `.claude/commands/` — test, lint, validate.
* Write: this is a web app. It does not link Zion-HAL, does not reuse `hal_service.proto` or `client_service.proto`, and is not part of the on-device build.
* Test: three suites — `test-api`, `test-gateway`, `test-web`. All three must pass.
* Migrations: alembic, and the gate enforces a **single head**. Check before adding one.

## How you validate

* Gate: `./.claude/validate.sh quick` (seconds) or `full` (adds build + tests). Run it before you claim done.
* Exit codes: `0` pass, `1`-`76` fail, `77` a check never ran. **77 is not a pass.**
* The gate and everything under `.claude/lib`, `hooks`, `commands`, `settings.json` is human-owned. Run it, never edit it.

## Do

* Keep the architectural boundary the gate checks: no on-device protos, no HAL coupling.
* Model the device link on Client-to-Server's shape (device dials out, persistent connection, presence = liveness) but keep it a separate protocol with its own pairing-token auth.
* Put device-side work in Zion-Configuration, coordinated from here — the HQ pairing section, token storage and outbound agent belong in that repo.
* Read `ARCHITECTURE.md` for the design and `PLAN.md` for phasing before changing structure.

## Don't

* **Don't link Zion-HAL or reuse its protos.** Any resemblance to Client/Server's proto sharing is coincidental, not a dependency.
* **Don't add a second alembic head.** The gate fails on it and the fix is a merge migration.
* **Don't confuse this with the two other UIs.** Zion-Configuration's WebConfig is local and single-device; Zion-Dashboard is a standalone browser app. HQ is fleet-wide and cloud-hosted.
* **Don't scope a loop here without confirming the remote is reachable** (`git ls-remote`) — `branch-push` fails late otherwise.

<!-- BEGIN loop-engine -->
## Do's and Don'ts (maintained by the Loop Engine)

Appended by the Loop Engine on loop close; curated by a human when approving a loop out of in-review/. Nothing outside this fence is engine-writable.

- (2026-07-30, loop 20260730-app-telemetry-daemon) Telemetry sample ingest added: `POST /devices/{device_id}/telemetry` (operator) and `GET /devices/{device_id}/telemetry/{sample_id}` (viewer) on `api/app/routers/telemetry.py`, backed by the pre-existing `telemetry_sample` table (phase1 migration). DO NOT rename the table to a bare `telemetry` without a human blessing — the loop's stated constraint said "new table named telemetry" but the table pre-existed as `telemetry_sample` and renaming would break the GET series router and risk a second alembic head. The accepted name is `telemetry_sample` pending human confirmation (see the loop's Lessons Learned F1).
- (2026-07-30, loop 20260730-app-telemetry-daemon) `make lint` was RED at baseline due to 8 pre-existing unused-import (F401) errors in `api/app/routers/devices.py`; cleared by `ruff check --fix` in the same commit as the telemetry work. If you see F401s reappear there, they are new, not pre-existing.
- (2026-07-30, loop 20260730-app-alarms-daemon) Device-reported 4-byte alarm ingest added on a NEW table `alarms` (model `DeviceAlarm` in `api/app/models/device_alarm.py`, migration `c1a2b3c4d5e6`, `down_revision=a40971629062`, single head). Endpoints on `api/app/routers/alarms.py`: `POST /devices/{device_id}/alarms` (operator, decodes hex `alarm_code` into major_id/sub_section/fault_type/severity, big-endian: byte0=MSB=major_id .. byte3=LSB=severity; `0x01020304`->(1,2,3,4)), `GET /devices/{device_id}/alarms` (viewer, lists `DeviceAlarm` rows with the 4 decoded fields), `POST /devices/{device_id}/alarms/{alarm_id}/clear` (operator, sets state=resolved; `clear`==`resolve`, no `cleared` enum value). `alarm_code` is `BigInteger` (unsigned 0xFFFFFFFF overflows int32). The pre-existing rule-based `alarm` table (`Alarm` model) is UNCHANGED; its `/alarms/{alarm_id}/acknowledge` and `/alarms/{alarm_id}/resolve` routes still operate on `Alarm`. The web UI `web/src/components/device/FaultsAlarmsPanel.vue` renders `DeviceAlarm` rows (4-byte fields + hex code) with a Clear button wired to the device-scoped clear endpoint; it no longer calls acknowledge/resolve on device alarms. **LESSON: repointing a shared device-scoped list route (`GET /devices/{device_id}/alarms`) from one table to another is a silent breaking change for any frontend consumer — grep `web/src/` for consumers BEFORE repointing, and add/extend a vitest covering the panel (`test-web` did not cover `FaultsAlarmsPanel.vue` so the gate was blind to the break until try 3).** The device-scoped rule-based `Alarm` list was lost (no replacement endpoint); the operator can still ack/resolve rule-based alarms by ID but cannot list them — a human should decide whether to add a replacement list route.
<!-- END loop-engine -->
