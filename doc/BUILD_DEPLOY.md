# Zion-HQ Build and Deployment

## Purpose and scope
Zion-HQ is the cloud fleet-management workspace. Its Makefile orchestrates a Python API, Python agent gateway, Vue web app, PostgreSQL, MinIO, Redis, and Keycloak development services. The README labels the product planning-stage; this guide documents the runnable local workflow without implying production readiness.

## 1. Prerequisites
- Docker and Docker Compose, Python 3.12, Node.js compatible with the web manifest (Node 22.18+ or 24.12+), and npm.
- Network access to install editable Python packages and web dependencies.
- A controlled development tenant for seed/login operations; never reuse the dev credentials in production.

## 2. Setup
```bash
make doctor
make install
make db-up
make migrate
make seed EMAIL=admin@example.com
```
`install` creates `.venv`, installs `./api[dev]` and `./agent-gateway[dev]`, and runs `npm install` in `web`. `db-up` starts Postgres, MinIO, Redis, and Keycloak, waits for readiness, creates `zionhq_test`, and creates the MinIO bucket.

## 3. Build and compile
```bash
make build
```
This runs `npm run build` in the Vue `web` package. The Python API and gateway are installed editable rather than compiled into a standalone artifact by the Makefile.

## 4. Test and lint
```bash
make test
make test-api
make test-gateway
make test-web
make lint
```
API and gateway tests use pytest against the configured test database; web tests use `npx vitest run`. Lint runs Ruff for Python and `npm run lint` plus `vue-tsc --noEmit` for web.

## 5. Packaging and artifacts
The Makefile has no release packaging target. Web build output is `web/dist`; Python environments and editable installs live in `.venv`. Database schema is managed by Alembic migrations. Docker Compose volumes persist Postgres, MinIO, and Keycloak state.

## 6. Deployment, install, and run
```bash
make run
make logs
make stop
make db-down
```
`run` starts the database, applies migrations, and backgrounds API (port 8000), gateway (gRPC port 50051), and Vite web (port 5173). It prints the LAN URLs and writes PID/log files under `.run`. Use one LAN IP consistently for login cookies. `make seed EMAIL=...` is conditional on a test database and creates a development tenant/admin. `DATABASE_URL`, `TEST_DATABASE_URL`, and `S3_ENDPOINT_URL` can be overridden.

## 7. Cleanup
```bash
make stop
make db-down
make clean
```
`stop` leaves database containers running; `db-down` stops them while preserving Docker volumes. `clean` removes `.venv`, `.run`, `web/node_modules`, `web/dist`, caches, and Python bytecode. Removing Docker volumes is a separate, destructive Compose operation and is not part of the Makefile.

## 8. Hardware, cloud, and manual verification caveats
This is a local multi-service development stack, not a production deployment recipe. Keycloak uses `admin/admin`, the seeded user uses `admin@example.com/devpassword`, MinIO uses development credentials, and HTTP is enabled. Cloud credentials, TLS, external identity, authorization policy, device connectivity, OTA signing, backups, and destructive fleet operations require separate controlled verification.
