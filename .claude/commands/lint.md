---
description: Lint all three HQ surfaces (ruff via .venv + node)
allowed-tools: Bash(make lint), Bash(make install), Bash(./.claude/validate.sh:*)
---

!`./.claude/validate.sh quick`

The gate wraps the linters plus the architectural checks (single alembic head,
no on-device proto leakage). No .venv/bin/ruff → make install first. Never
report a 77 as a pass.
