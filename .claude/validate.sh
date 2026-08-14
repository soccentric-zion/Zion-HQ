#!/usr/bin/env bash
# Zion-HQ — per-repo validation gate.  See .claude/lib/validate-lib.sh.
#
#   quick   seconds. Migration + proto + config sanity, then the three linters.
#   full    minutes. test-api, test-gateway, test-web.
#
# HQ is a standalone cloud app. It does NOT link Zion-HAL and does NOT reuse
# hal_service.proto / client_service.proto — its only integration point is the
# device pairing link to Zion-Configuration. The first check keeps it that way.
set -uo pipefail
# shellcheck source=lib/validate-lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/validate-lib.sh"

TIER="$(tier_or_die "${1:-quick}")"

# --- quick -----------------------------------------------------------------

# Deliberate architectural boundary (ARCHITECTURE.md §7). Drift here is the kind
# that looks like convenient reuse right up until HQ is coupled to the on-device
# wire contract and can't be deployed independently.
assert "no on-device wire contracts leaked into HQ" \
  'hits=""
   for f in $(find proto api agent-gateway -type f \( -name "*.proto" -o -name "*.py" \) 2>/dev/null); do
     strip_comments < "$f" \
       | grep -qE "hal_service\.proto|client_service\.proto|zion\.stream" \
       && hits="$hits $f"
   done
   [ -z "$hits" ] || { echo "HQ must not reuse the on-device protos:"; echo "$hits"; exit 1; }'

assert "no Zion-HAL build coupling" \
  '! grep -rqE "add_subdirectory\(.*Zion-HAL|\.\./Zion-HAL" . --include="*.txt" --include="*.cmake" --include="*.toml" 2>/dev/null'

check "alembic migrations have a single head" "python3" \
  'downs=$(grep -rhoP "down_revision\s*=\s*[\x27\"]\K[^\x27\"]+" migrations/ 2>/dev/null | sort)
   revs=$(grep -rhoP "^revision\s*=\s*[\x27\"]\K[^\x27\"]+" migrations/ 2>/dev/null | sort)
   heads=$(comm -23 <(echo "$revs") <(echo "$downs") | grep -c .)
   [ "${heads:-0}" -le 1 ] || { echo "$heads alembic heads — merge them before migrating"; exit 1; }'

check "HQ protos parse" "python3" \
  'ls proto/*.proto >/dev/null 2>&1 || exit 0
   for f in proto/*.proto; do
     grep -q "^syntax" "$f" || { echo "$f has no syntax declaration"; exit 1; }
   done'

# make lint-api/lint-gateway call $(VENV)/bin/ruff directly. With no virtualenv
# that surfaces as `make: *** Error 127` — exit 2, which would read as a lint
# FAIL when in fact nothing was linted at all. Gate on the venv instead.
if [ -x .venv/bin/ruff ]; then
  check "python + node linters" "python3 node npm" 'make lint'
else
  block "python + node linters" "not run; no .venv/bin/ruff — run: make install"
fi

[ "$TIER" = "quick" ] && { report "$TIER"; exit $?; }

# --- full ------------------------------------------------------------------

# The api suite wants Postgres; docker brings it up via `make db-up`.
check "api tests" "python3 docker" 'make test-api'
check "gateway tests" "python3" 'make test-gateway'
check "web tests" "node npm" 'make test-web'

report "$TIER"
