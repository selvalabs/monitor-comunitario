# Production Deployment Readiness

This document describes how to prepare the project for a future production deployment.

It does not cover the actual VPS setup, domain, SSL, reverse proxy, or CI/CD deployment automation. Those steps should be handled in separate issues.

## Deployment modes

The project currently supports these deployment-oriented modes:

```text
1. Local development with SQLite
2. Local Docker Compose with Postgres
3. External Postgres/Supabase through Docker Compose
4. Production-like Docker Compose with .env.production
```

## Required production files

Create a production environment file from the example:

```powershell
Copy-Item .env.production.example .env.production
```

Never commit `.env.production`.

## Required environment variables

### Application

```env
APP_ENV=production
APP_TIMEZONE=America/Sao_Paulo
```

### Database

```env
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>?sslmode=require
```

For Supabase, prefer the pooled connection string when deploying through containers, especially on VPS hosts without IPv6 access to the direct database hostname.

Example format:

```env
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@aws-<pooler-index>-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

Use the pooler host shown by the Supabase project dashboard/API for the specific project. Do not infer the pooler index from another project.

### Admin access

All `/admin/*` endpoints require:

```env
ADMIN_API_KEY=<strong-admin-api-key>
```

The admin dashboard is available by direct URL:

```text
/admin
```

The key is entered manually in the browser and stored only in `sessionStorage`.

Do not hardcode `ADMIN_API_KEY` into frontend JavaScript.

## Production-like Docker Compose

The production-like compose file uses an external database and a local containerized API/worker.

Start with:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production up --build
```

Run in detached mode:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

Stop services:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production down
```

## Guarded VPS deployment

On the Venusiana VPS, deployment can be executed through the guarded `docker-ops` wrapper instead of direct Docker daemon access:

```bash
VENUSIANA_CHANNEL_PLATFORM=telegram /opt/data/ops/docker-ops/docker-ops compose-up monitor-comunitario
```

The guard is expected to:

```text
run only the fixed project path
use docker-compose.production.yml
use .env.production with file mode 600
require Telegram admin or approval before deploy
allow status/logs access for the deployed containers
```

The first successful guarded deploy should finish with:

```text
DOCKER_OPS_COMPOSE_UP_OK project=monitor-comunitario
```

Docker Compose may create runtime container names with a numeric suffix:

```text
monitor-comunitario-api-1
monitor-comunitario-worker-1
monitor-comunitario-migrate-1
```

Ensure the Docker guard allowlist matches the real Compose container names before relying on `status` or `logs` checks.

## Migration flow

The `migrate` service runs before the API and worker:

```bash
uv run monitor-comunitario db-upgrade
```

Manual migration command:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production run --rm migrate
```

Check current migration locally or inside a container:

```powershell
uv run monitor-comunitario db-current
```

## Operational checks

### Liveness

```text
GET /health
```

Expected result:

```json
{
  "status": "ok",
  "environment": "production",
  "timezone": "America/Sao_Paulo"
}
```

### Readiness

```text
GET /ready
```

Expected result when the database is available:

```json
{
  "status": "ready",
  "database": "ok"
}
```

If the database is unavailable, `/ready` returns `503`.

The production compose file uses `/ready` as the API container healthcheck.

### Admin diagnostics

```text
GET /admin/diagnostics
```

Required header:

```http
X-Admin-API-Key: <strong-admin-api-key>
```

This endpoint returns frontend-friendly operational metadata:

```text
environment
timezone
database status
scheduler settings
notification provider
latest monitoring run
```

### Admin dashboard

```text
/admin
```

Use this page to:

```text
enter the admin key
refresh operational diagnostics
check latest monitoring run
inspect monitoring history
trigger a manual monitoring cycle
```

## Logs and troubleshooting

Show service status:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production ps
```

Show API logs:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production logs -f api
```

Show worker logs:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production logs -f worker
```

Show migration logs:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production logs migrate
```

When using the guarded VPS wrapper, use the real container names reported by Compose or `docker-ops ps`:

```bash
/opt/data/ops/docker-ops/docker-ops ps
/opt/data/ops/docker-ops/docker-ops status monitor-comunitario-api-1
/opt/data/ops/docker-ops/docker-ops logs monitor-comunitario-api-1 --tail 120
/opt/data/ops/docker-ops/docker-ops status monitor-comunitario-worker-1
/opt/data/ops/docker-ops/docker-ops logs monitor-comunitario-worker-1 --tail 120
```

If `docker-ops status monitor-comunitario-api` returns an image-like object or `No such container`, check whether Compose created `monitor-comunitario-api-1` instead. If the suffixed name returns `container not allowlisted`, update the guard allowlist before continuing validation.

Restart API:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production restart api
```

Restart worker:

```powershell
docker compose -f docker-compose.production.yml --env-file .env.production restart worker
```

## Basic deployment checklist

Before a real deployment:

```text
[ ] .env.production exists and is not committed
[ ] DATABASE_URL points to the production database
[ ] Supabase deployments use the project-specific pooler host when IPv4 is required
[ ] ADMIN_API_KEY is strong and private
[ ] migrations run successfully
[ ] /health returns 200
[ ] /ready returns 200
[ ] /admin opens by direct URL
[ ] /admin/diagnostics works with X-Admin-API-Key
[ ] worker logs show scheduled execution
[ ] docker-ops allowlist matches the real Compose container names when using guarded VPS deploy
[ ] snapshots volume is writable
```

## Out of scope

The following items should be handled in future issues:

```text
VPS provisioning
domain and DNS
SSL certificates
reverse proxy with Traefik or Nginx
CI/CD deployment automation
secret manager integration
WhatsApp/Evolution production delivery
```
