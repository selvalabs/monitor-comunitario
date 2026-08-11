# Internal Endpoint Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make public Monitor API requests unable to reach `/internal/*` while preserving the authenticated Monitor integrations.

**Architecture:** Assemble two FastAPI applications from shared lifecycle and route modules. `api` serves public/member/admin routers through Traefik; `api-internal` serves only internal routers over a private Monitor network and the narrow existing Cloudflare tunnel route.

**Tech Stack:** FastAPI, Docker Compose, Cloudflared, pytest, Traefik labels.

---

### Task 1: Split application assembly

**Files:**
- Create: `src/monitor_comunitario/api/internal.py`
- Modify: `src/monitor_comunitario/api/main.py`
- Test: `tests/unit/test_internal_app_isolation.py`

- [ ] Write failing tests asserting the public app returns `404` for `/internal/hermes/events`, `/internal/email/inbound`, and `/internal/monitor-bot/registration-events`, while the internal app recognizes those routes.
- [ ] Run `pytest tests/unit/test_internal_app_isolation.py -p no:cacheprovider` and verify failure because `internal.app` does not exist and public routes remain mounted.
- [ ] Extract the shared FastAPI lifecycle, security headers, `/health`, and `/ready` setup into a reusable factory. Mount only public routers in `main.app`; mount `routes_hermes_internal`, `routes_email_internal`, `routes_monitor_bot`, and the Hermes callback router in `internal.app`.
- [ ] Re-run the focused test and verify both route-boundary assertions pass.
- [ ] Commit: `refactor(api): split public and internal applications`.

### Task 2: Add private Monitor service topology

**Files:**
- Modify: `docker-compose.production.yml`
- Modify: `ops/cloudflared/config.yml`
- Modify: `docs/DEPLOYMENT.md`

- [ ] Add compose assertions using `docker compose -f docker-compose.production.yml config` that `api-internal` has no `ports` or Traefik labels, Cloudflared depends on it, and the `api` service remains the only Traefik service.
- [ ] Run the assertion before edits and verify `api-internal` is absent.
- [ ] Add `api-internal` from the same image, serving `monitor_comunitario.api.internal:app` on port 8000, with healthcheck and the Monitor-only private network. Move Cloudflared origin to `api-internal:8000`. Keep the existing hostname and exact email-inbound path allowlist.
- [ ] Document the external attachment required only for `hermes-monitor-comunitario`, and change the Monitor bot internal URL to the internal service name.
- [ ] Re-run compose config and assert no public port or Traefik label belongs to `api-internal`.
- [ ] Commit: `feat(deploy): add private internal API service`.

### Task 3: Verify integration contracts

**Files:**
- Modify: `tests/unit/test_hermes_internal_api.py`
- Modify: `tests/unit/test_monitor_bot_api.py` or the existing Monitor-bot route test file
- Modify: `tests/unit/test_email_ingress.py` or the existing email ingress route test file
- Modify: `docs/agent/HANDOFF.md`

- [ ] Add focused tests for secret rejection and accepted authenticated calls through `internal.app` for Hermes, Monitor bot, and email ingress.
- [ ] Run each focused test before any behavior changes and verify the test captures the required route boundary or existing failure mode.
- [ ] Adjust only imports/fixtures needed to use `internal.app`; retain current HMAC and service-secret code unchanged.
- [ ] Run `ruff check .`, `mypy src`, `pytest -p no:cacheprovider`, Worker `npm test`, and `docker compose -f docker-compose.production.yml config --quiet`.
- [ ] Commit: `test(api): cover internal service boundary`.

### Task 4: Controlled production rollout

**Files:**
- No repository changes beyond the prior tasks.

- [ ] Obtain separate explicit production authorization.
- [ ] Create a dedicated Monitor backup containing only the Monitor Compose revision, protected environment file metadata, Cloudflared config, and Monitor dispatcher script; do not read or copy secrets into logs.
- [ ] Preflight current Monitor containers, Compose configuration, health endpoints, and current Docker network attachments.
- [ ] Deploy only Monitor Compose services, attach only `hermes-monitor-comunitario` to the named private Monitor network, and update only the Monitor dispatcher/base URL configuration without exposing its secret.
- [ ] Verify public `404` boundary, public health/readiness, Cloudflare email authenticated delivery, Hermes event access, Monitor bot access, absence of `api-internal` Traefik labels/ports, and Monitor-only logs.
- [ ] On any contract failure, revert only the Monitor Compose revision and remove only the new Monitor network attachment.
