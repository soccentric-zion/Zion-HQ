---
description: Run HQ's three suites — api (needs Postgres via docker), gateway, web
allowed-tools: Bash(make test:*), Bash(make test-api), Bash(make test-gateway), Bash(make test-web), Bash(make db-up)
---

!`make test-gateway && make test-web && make test-api`

Gateway and web first (no external deps), api last — it wants Postgres, which
make db-up brings up via docker. If docker is unavailable, report test-api as
not run (that is a provisioning gap, not a pass and not a code failure). HQ is a
standalone cloud app: it must not link Zion-HAL or reuse the on-device protos,
and the quick gate checks that boundary.
