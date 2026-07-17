# Operations

## Overview

The project exposes public pages, public registration, member access and protected admin endpoints.

Operational endpoints are intentionally simple and frontend-friendly so they can be consumed by the internal admin dashboard.

## Public endpoints

### `GET /health`

Liveness check. It only confirms that the API process is responding.

Example response:

```json
{
  "status": "ok",
  "environment": "production",
  "timezone": "America/Sao_Paulo"
}
```

### `GET /ready`

Readiness check. It verifies that the API can execute a minimal database query.

Successful response:

```json
{
  "status": "ready",
  "database": "ok"
}
```

If the database is unavailable, the endpoint returns `503 Service Unavailable`:

```json
{
  "status": "not_ready",
  "database": "error"
}
```

### `GET /`

Serves the public registration page.

### `GET /member`

Serves the resident member area.

### `POST /users`

Creates a public resident/address registration and returns a one-time private access code.

### `POST /member/access`

Allows a resident to access their member area with phone + private code.

## Protected admin endpoints

All `/admin/*` API endpoints require the `X-Admin-API-Key` header.

```http
X-Admin-API-Key: <strong-admin-api-key>
```

The expected value is configured through:

```env
ADMIN_API_KEY=<strong-admin-api-key>
```

### Diagnostics and runs

```text
GET  /admin/diagnostics
GET  /admin/runs
GET  /admin/runs/latest
GET  /admin/runs/{run_id}
POST /admin/runs/manual
```

`GET /admin/diagnostics` returns operational metadata for admin usage.

Example response:

```json
{
  "status": "ok",
  "environment": "production",
  "timezone": "America/Sao_Paulo",
  "database": {
    "status": "ok"
  },
  "scheduler": {
    "enabled": true,
    "hour": 6,
    "minute": 0
  },
  "notifications": {
    "provider": "app",
    "evolution_enabled": false
  },
  "latest_run": null
}
```

### User management

```text
GET    /admin/users
GET    /admin/users/{user_id}
PATCH  /admin/users/{user_id}
DELETE /admin/users/{user_id}
```

These routes are protected because they expose or modify resident registration data.

Public numeric-ID access to users is intentionally not exposed. Residents should use `/member/access` with phone + private code.

### Notification management

```text
GET    /admin/notifications
GET    /admin/users/{user_id}/notifications
PATCH  /admin/notifications/{notification_id}/read
```

These routes are protected because notifications can reveal a resident/address relationship with a public outage notice.

## Admin diagnostics dashboard

The project serves a simple internal admin dashboard at:

```text
/admin
```

The dashboard is intentionally not linked from the public homepage. It is meant for direct internal access by the operator.

The page itself is public static HTML, but protected data requests still require `ADMIN_API_KEY`. The key is not hardcoded into JavaScript. The operator enters it manually in the browser, and the frontend stores it only in `sessionStorage` for the current browser session.

The dashboard sends protected requests with:

```http
X-Admin-API-Key: <strong-admin-api-key>
```

It renders:

```text
API status
Database readiness
Scheduler configuration
Notification configuration
Latest monitoring run status
Latest counts for notices, users, matches and notifications
Manual run button
Monitoring history table
```

## Local admin usage

Start the API with an admin key:

```powershell
$env:ADMIN_API_KEY="change-me-local-admin-key"
uv run uvicorn monitor_comunitario.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/admin
```

Use the configured key in the dashboard form.

Do not commit real admin keys.

## Post-deploy validation

After a production-like or guarded VPS deploy, validate the API before announcing that the service is ready:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
curl -fsS http://127.0.0.1:8000/
```

Then validate protected admin diagnostics with the configured key:

```bash
curl -fsS \
  -H "X-Admin-API-Key: <strong-admin-api-key>" \
  http://127.0.0.1:8000/admin/diagnostics
```

For guarded VPS deployments, also inspect API and worker logs through the Docker guard using the real Compose container names:

```bash
/opt/data/ops/docker-ops/docker-ops logs monitor-comunitario-api-1 --tail 120
/opt/data/ops/docker-ops/docker-ops logs monitor-comunitario-worker-1 --tail 120
```

If the API port is not reachable from the agent container, validate from the host network or through the configured reverse proxy after it is added.
