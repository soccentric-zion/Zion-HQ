# Zion-HQ — top-level entry point.
# Wraps: docker compose (Postgres/MinIO/Redis), the Python venv (api +
# agent-gateway), and the Vue frontend. See IMPLEMENTATION_PLAN.md §0.

SHELL := /bin/bash
CURDIR := $(shell pwd)
VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
COMPOSE := docker compose -f infra/docker-compose.yml -p zionhq
RUN_DIR := $(CURDIR)/.run

DATABASE_URL ?= postgresql+asyncpg://zionhq:zionhq@localhost:5432/zionhq
TEST_DATABASE_URL ?= postgresql+asyncpg://zionhq:zionhq@localhost:5432/zionhq_test
S3_ENDPOINT_URL ?= http://localhost:9000

.PHONY: help doctor install db-up db-down migrate seed run stop logs \
        test test-api test-gateway test-web lint lint-api lint-gateway lint-web \
        build clean

help:
	@echo "Zion-HQ"
	@echo ""
	@echo "  make doctor        check prerequisites (docker, python3, node)"
	@echo "  make install       create venv, install api/agent-gateway/web deps"
	@echo "  make db-up         start Postgres/MinIO/Redis (docker compose)"
	@echo "  make db-down       stop them (data persists in docker volumes)"
	@echo "  make migrate       alembic upgrade head"
	@echo "  make seed EMAIL=you@example.com   seed a dev tenant + admin user"
	@echo "  make run           start db + api + agent-gateway + web in the background"
	@echo "  make stop          stop everything 'make run' started"
	@echo "  make logs          tail logs for the background services"
	@echo "  make test          run api + agent-gateway + web test suites"
	@echo "  make lint          run ruff (api, agent-gateway) + eslint/oxlint (web)"
	@echo "  make build         build the web frontend for production"
	@echo "  make clean         remove venv, node_modules, caches, dist, run logs"

doctor:
	@command -v docker >/dev/null || { echo "docker not found"; exit 1; }
	@command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
	@command -v node >/dev/null || { echo "node not found"; exit 1; }
	@echo "all prerequisites found"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install: $(VENV)/bin/activate
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e ./api[dev] -e ./agent-gateway[dev]
	cd web && npm install

db-up:
	$(COMPOSE) up -d
	@echo "waiting for postgres..."
	@until docker exec $$($(COMPOSE) ps -q postgres) pg_isready -U zionhq >/dev/null 2>&1; do sleep 1; done
	@docker exec $$($(COMPOSE) ps -q postgres) psql -U zionhq -d zionhq -tc \
		"SELECT 1 FROM pg_database WHERE datname='zionhq_test'" | grep -q 1 || \
		docker exec $$($(COMPOSE) ps -q postgres) createdb -U zionhq zionhq_test
	@echo "waiting for minio..."
	@until docker exec $$($(COMPOSE) ps -q minio) mc ready local >/dev/null 2>&1; do sleep 1; done
	@docker run --rm --network zionhq_default -e MC_HOST_local=http://zionhq:zionhq-dev-secret@minio:9000 \
		minio/mc mb -p local/zionhq >/dev/null 2>&1 || true
	@echo "waiting for keycloak (can take ~30s on first boot)..."
	@until curl -sf http://localhost:8081/realms/zionhq/.well-known/openid-configuration >/dev/null 2>&1; do sleep 2; done
	@echo "postgres, minio (bucket: zionhq), redis, keycloak (realm: zionhq) ready"

db-down:
	$(COMPOSE) down

migrate:
	ZIONHQ_DATABASE_URL=$(DATABASE_URL) $(VENV)/bin/alembic upgrade head

seed:
	@test -n "$(EMAIL)" || { echo "usage: make seed EMAIL=you@example.com"; exit 1; }
	cd api && ZIONHQ_DATABASE_URL=$(DATABASE_URL) $(PY) -m scripts.seed_dev --email $(EMAIL)

# Each service is launched as `(cd dir && exec env VARS nohup cmd) &` --
# the `exec` makes the subshell replace its own process image with the
# final command instead of forking a child for it, so `$!` (captured right
# after) is the PID of the actual long-running server, not a wrapper shell.
# Without this, `make stop` kills the wrapper and orphans the real process.
run: db-up migrate
	@mkdir -p $(RUN_DIR)
	@echo "starting api, agent-gateway, web..."
	@(cd api && exec env ZIONHQ_DATABASE_URL=$(DATABASE_URL) ZIONHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		ZIONHQ_OIDC_ISSUER=http://$$(hostname -I | awk '{print $$1}'):8081/realms/zionhq \
		nohup $(PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > $(RUN_DIR)/api.log 2>&1) & echo $$! > $(RUN_DIR)/api.pid
	@(cd agent-gateway && exec env ZIONHQ_DATABASE_URL=$(DATABASE_URL) ZIONHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		nohup $(PY) -m gateway.server > $(RUN_DIR)/gateway.log 2>&1) & echo $$! > $(RUN_DIR)/gateway.pid
	@(cd web && exec nohup ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 > $(RUN_DIR)/web.log 2>&1) & echo $$! > $(RUN_DIR)/web.pid
	@sleep 1
	@LAN_IP=$$(hostname -I 2>/dev/null | awk '{print $$1}'); \
	echo "web:      http://$$LAN_IP:5173   (use this on every device, including this host --"; \
	echo "                                  login redirects always go to the LAN IP, so mixing"; \
	echo "                                  it with http://localhost:5173 splits your session"; \
	echo "                                  cookie across two origins)"; \
	echo "api:      http://$$LAN_IP:8000"; \
	echo "keycloak: http://$$LAN_IP:8081/admin  (admin/admin)"; \
	echo "gateway:  $$LAN_IP:50051 (gRPC)"; \
	echo ""; \
	echo "login:    admin@example.com / devpassword"; \
	echo "          (first time: make seed EMAIL=admin@example.com to pre-invite it as admin)"; \
	echo ""; \
	echo "logs:     make logs   |   stop:  make stop"

stop:
	-@for f in $(RUN_DIR)/*.pid; do [ -f "$$f" ] && kill $$(cat "$$f") 2>/dev/null; rm -f "$$f"; done
	@echo "background services stopped (db left running -- 'make db-down' to stop it too)"

logs:
	@tail -n 100 -f $(RUN_DIR)/api.log $(RUN_DIR)/gateway.log $(RUN_DIR)/web.log

test: test-api test-gateway test-web

test-api:
	cd api && ZIONHQ_TEST_DATABASE_URL=$(TEST_DATABASE_URL) ZIONHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		$(VENV)/bin/python -m pytest -q

test-gateway:
	cd agent-gateway && ZIONHQ_TEST_DATABASE_URL=$(TEST_DATABASE_URL) ZIONHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		$(VENV)/bin/python -m pytest -q

test-web:
	cd web && npx vitest run

lint: lint-api lint-gateway lint-web

lint-api:
	$(VENV)/bin/ruff check api

lint-gateway:
	$(VENV)/bin/ruff check agent-gateway

lint-web:
	cd web && npm run lint && npx vue-tsc --noEmit

build:
	cd web && npm run build

clean:
	rm -rf $(VENV) $(RUN_DIR) web/node_modules web/dist web/.eslintcache
	find . -name __pycache__ -o -name "*.egg-info" -o -name .ruff_cache -o -name .pytest_cache | xargs rm -rf
