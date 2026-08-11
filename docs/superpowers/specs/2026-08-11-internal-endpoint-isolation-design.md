# Internal Endpoint Isolation Design

**Issue:** #140

## Goal

Remove `/internal/*` contracts from the public Monitor API entrypoint while
preserving the authenticated Hermes, email-ingress, and registration-bot flows.

## Scope

- Split the current FastAPI assembly into a public application and an internal
  application.
- Add `api-internal` to the Monitor production Compose project without Traefik
  labels or published ports.
- Move the Monitor-only Hermes container onto a dedicated private Docker
  network shared with `api-internal`.
- Point the Monitor Cloudflare email tunnel at `api-internal`.
- Preserve existing HMAC and service-secret checks.

## Out Of Scope

- Any non-Monitor VPS container, network, tunnel, proxy, domain, or database.
- Credential rotation, database migration, public product behavior, or changes
  to the Hermes WhatsApp policy.

## Architecture

```text
Public browser
  -> Traefik -> api-public
                 - public, member, and admin routes only

Cloudflare email tunnel
  -> api-internal
                 - /internal/email/inbound only

Hermes Monitor container
  -> private Monitor network -> api-internal
                 - Hermes callback and event contracts only

Monitor Telegram bot
  -> Monitor Compose network -> api-internal
                 - restricted bot contract only
```

`api-public` and `api-internal` use the same image and lifecycle validation,
but mount disjoint routers. `api-internal` has no Traefik labels and no host
port. Its only callers are the Monitor-specific Cloudflare tunnel, Hermes
container, and Monitor Telegram bot. Application-level secrets remain required
for every internal contract; network location is defense in depth.

## Route Ownership

`api-public` keeps web, registration, member, outage, and admin routers plus
`/health` and `/ready`.

`api-internal` owns the Hermes event router, Hermes callback route, Monitor
bot router, and email ingress router. It also exposes `/health` and `/ready`
for private container health checks only.

The public API must return `404` for each former `/internal/*` route. It must
not redirect those requests or reveal an alternate internal hostname.

## Network And Deployment

The Monitor Compose project defines a named private network for `api-internal`.
The existing Monitor-only Hermes container is attached to that network during
the controlled deployment. No other container is attached. Cloudflared reaches
`api-internal` through the Monitor Compose network and retains its current
hostname/path allowlist.

Deployment requires a dedicated Monitor backup, `docker compose config --quiet`,
image build, migrations, and an explicit rollback command that removes only the
new Monitor services/network attachment and restores the prior Monitor Compose
revision. Production execution requires separate explicit approval.

## Acceptance Tests

1. Public host: `/internal/email/inbound`, Hermes routes, and Monitor-bot
   routes return `404`.
2. Public health, registration, member access, and admin session flows remain
   available.
3. Cloudflare email ingress reaches only `api-internal` and receives the
   existing authenticated success response.
4. Hermes Monitor reaches its routes through the private Docker network and is
   rejected without its existing secret.
5. Telegram bot reaches its restricted route through `api-internal` and is
   rejected without its existing service key.
6. `api-internal` has no Traefik labels, no published port, and no public DNS
   route beyond the existing narrow Cloudflare email path.

## Risks And Rollback

The principal risk is a caller retaining the former API hostname. The rollout
therefore validates each internal caller before the public route is removed.
If any required contract fails, rollback restores the prior Monitor Compose
revision and its original single API service. No database state changes are
part of this work.
