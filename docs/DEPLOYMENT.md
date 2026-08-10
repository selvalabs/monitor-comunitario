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

### Trusted proxy

The API ignores `X-Forwarded-For` unless the direct peer belongs to an explicitly trusted proxy IP or CIDR list:

```env
TRUSTED_PROXY_IPS=172.16.15.1/32
```

Use the actual Docker bridge gateway or proxy network discovered during preflight. Do not copy this example blindly. Leave it empty when the proxy path is not verified; the application will then use the direct peer address safely.

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

### Registration verification

Production registration is fail-closed and requires email OTP followed by WhatsApp confirmation.

```env
EMAIL_VERIFICATION_ENABLED=true
EMAIL_VERIFICATION_TTL_SECONDS=900
EMAIL_VERIFICATION_MAX_ATTEMPTS=5
EMAIL_PROVIDER=brevo
BREVO_API_KEY=<brevo-api-key>
BREVO_API_URL=https://api.brevo.com/v3/smtp/email
EMAIL_FROM=monitor@monitor-mail.soberania.cloud

# SMTP fallback, only when EMAIL_PROVIDER=smtp
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USERNAME=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_TLS=true
HERMES_CALLBACK_SECRET=<strong-hermes-callback-secret>
HERMES_EVENT_API_SECRET=<strong-hermes-event-api-secret>
MEMBER_AREA_URL=https://monitorcomunitario.soberania.cloud/member
```

After the email OTP is verified, Monitor Comunitario creates a `member_phone_confirmation_requested` event in `hermes_events`. Hermes consumes that event, selects the approved `member_phone_confirmation_v1` template, and sends it through Hermes' own WhatsApp connection. The Monitor does not store WhatsApp gateway credentials, call Evolution, or receive a gateway webhook.

When the resident replies `OK` or `CANCELAR`, Hermes calls:

```text
POST /users/internal/hermes/phone-confirmation
X-Hermes-Callback-Secret: <strong-hermes-callback-secret>
```

Only exact `OK` activates the phone and creates the member record. `CANCELAR` removes the pending registration; no response lets the Redis request expire. After confirmation, Monitor creates a `member_phone_confirmation_completed` event for Hermes to send the approved access-code message.

Brevo is the outbound transactional provider for this flow. Cloudflare Email Routing is a separate inbound service and is not called by the Monitor API. The WhatsApp connection, credentials, inbound message handling, and delivery retries remain owned by Hermes. Configure those on the Hermes side, never in `.env.production` for Monitor Comunitario.

Hermes polls the internal event contract with `X-Hermes-Event-Secret`:

```text
GET /internal/hermes/events?event_type=member_phone_confirmation_requested
PATCH /internal/hermes/events/{id}
```

Polling atomically changes events from `created` to `queued`. Hermes acknowledges delivery with `{"status":"processed"}` or `{"status":"failed","error_message":"..."}`. The endpoint exposes only the two resident WhatsApp event types and does not grant database access.

### Admin access

All `/admin/*` endpoints require:

```env
ADMIN_API_KEY=<strong-admin-api-key>
```

The admin dashboard is available by direct URL:

```text
/admin
```

The key is entered once to create a short-lived HttpOnly admin session cookie. The key is not stored in browser storage.

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
[ ] /admin/diagnostics works with the admin session cookie and CSRF token
[ ] worker logs show scheduled execution
[ ] docker-ops allowlist matches the real Compose container names when using guarded VPS deploy
[ ] snapshots volume is writable
```

## Telegram registration bot

The existing `monitor-comunitario-telegram-bot` service runs the restricted
registration-support bot. It has no published port and calls only the private
API through `X-Monitor-Bot-Key`.

Required protected environment values are:

```text
MONITOR_BOT_API_KEY=<dedicated-monitor-bot-api-key>
MONITOR_BOT_API_URL=http://monitor-comunitario-api:8000
MONITOR_TELEGRAM_ENABLED=true
MONITOR_TELEGRAM_BOT_TOKEN=<telegram-bot-token>
MONITOR_TELEGRAM_ALLOWED_USER_IDS=<comma-separated-telegram-user-ids>
```

Enable it explicitly after the API is healthy:

```bash
/opt/data/ops/docker-ops/docker-ops compose-up monitor-comunitario
```

The bot does not receive `BREVO_API_KEY`, does not access PostgreSQL directly,
and cannot answer a resident's WhatsApp confirmation. Do not enable the
profile until the dedicated key and Telegram allowlist are present in the
protected production environment.

## Out of scope

The following items should be handled in future issues:

```text
VPS provisioning
domain and DNS
SSL certificates
reverse proxy with Traefik or Nginx
CI/CD deployment automation
secret manager integration
Hermes WhatsApp production delivery
```
