# Hermes agent bootstrap proposal

Issue: #37  
Status: Implemented through internal escalation/dashboard bootstrap  
Last updated: 2026-07-25

## Purpose

Hermes is the proposed communication boundary for Monitor Comunitario notifications, resident support and operational escalation.

The first goal is not to send messages. The first goal is to create a deterministic, auditable contract that says what should be communicated, why, to whom, by which approved template and whether human escalation is required.

## Current project boundary

Monitor Comunitario already owns:

- Celesc scraping;
- outage notice parsing;
- notice persistence;
- address matching;
- in-app notification creation;
- admin diagnostics and monitoring run history.

Hermes should not own those decisions. Hermes should receive events after Monitor Comunitario has decided that something relevant happened.

## Target component responsibilities

### Monitor Comunitario

- Emits event records.
- Owns resident registration and address data.
- Owns matching decisions and confidence levels.
- Owns admin approval requirements.
- Owns the official persisted audit source for the application.

### Hermes

- Reads pending communication/support events.
- Applies deterministic classifiers or explicit intents.
- Selects approved templates.
- Sends through configured delivery adapters when enabled.
- Escalates operational or sensitive events to Frank.
- Records processing and delivery status.

### WhatsApp gateway

- Delivers messages only after Hermes has selected an approved template.
- Does not decide content policy.
- Does not call LLM providers.
- Can be Evolution API or another provider.

### Telegram channel for Frank

- Receives internal operational escalations.
- Does not replace persisted audit records.
- Should be considered a convenience channel, not the source of truth.

### LLM/provider

- May be used only for internal/admin assistance.
- Must not participate in resident-facing support or notification replies by default.
- Must not generate resident-facing final text unless a future ADR explicitly changes this policy.

## Event lifecycle

Initial statuses:

```text
created
queued
processed
failed
escalated
```

Initial event fields:

```text
id
event_type
status
source
channel
recipient_phone
intent
template_key
payload_json
llm_allowed
error_message
created_at
processed_at
```

The current bootstrap adds this as `hermes_events`.

## Initial event types

```text
notification_ready
support_message_received
support_response_ready
admin_summary_requested
scraper_failed
parser_failed
worker_failed
notification_delivery_failed
gateway_down
```

These event types are intentionally small. More event types should be added only when a real producer or consumer needs them.

## Resident-facing intents

```text
HELP
WHAT_IS_THIS
NOT_CELESC
ALERT_EXPLANATION
ACCESS_MEMBER_AREA
LOST_ACCESS_CODE
UPDATE_ADDRESS
OPT_OUT
DELETE_DATA_REQUEST
WRONG_ALERT_FEEDBACK
EMERGENCY
OUT_OF_SCOPE
UNKNOWN_ESCALATE
```

Unknown, privacy-sensitive and deletion-related intents should create an escalation path even when a deterministic acknowledgment is sent.

## Template rules

Templates must be:

- versioned by key, for example `alert_explanation_v1`;
- deterministic;
- approved before use;
- short enough for WhatsApp delivery later;
- explicit that Monitor Comunitario is not Celesc;
- careful with probabilistic language such as "pode afetar";
- stored with the event audit record through `template_key`.

Resident-facing templates must have:

```text
user_facing = true
llm_allowed = false
```

The bootstrap enforces this in `create_hermes_event`.

## Integration plan

### Phase 1 - Internal event audit

Implemented:

- deterministic catalog;
- `hermes_events` table;
- event creation service;
- tests for catalog, model and LLM guardrail.

No external delivery.

### Phase 2 - Producers

Implemented producers:

- create `notification_ready` when an in-app notification is created;
- create `worker_failed` from monitoring failures;
- create `admin_approval_pending` when a new resident registration starts unapproved.

Still future:

- create `scraper_failed` or `parser_failed` if scraper/parser errors are split into finer event types;
- create privacy/support events from future resident support entrypoints.

This phase still may avoid external delivery.

### Phase 3 - Admin visibility

Add protected admin endpoints and dashboard visibility:

```text
GET /admin/hermes/events
GET /admin/hermes/events/{event_id}
PATCH /admin/hermes/events/{event_id}/status
```

These endpoints must require the authenticated HttpOnly admin session and CSRF token.

Implemented in the backend and dashboard:

- list recent Hermes events;
- inspect one Hermes event through the API;
- mark events manually as `processed` or `escalated` from the dashboard.

### Phase 4 - Local Hermes poller

Add a local worker or CLI command that reads `created` events and transitions them to:

```text
queued
processed
failed
escalated
```

At first, this can process only `app` or `noop` channels and write status. It should not send external messages.

Implemented as `monitor-comunitario hermes-process`.

### Phase 5 - Internal escalation

Add Telegram escalation for Frank behind configuration:

```text
HERMES_TELEGRAM_ENABLED=false
HERMES_TELEGRAM_BOT_TOKEN=
HERMES_TELEGRAM_CHAT_ID=
```

Only internal escalation events should use this channel.

Implemented behind configuration. Telegram remains disabled by default.

### Phase 6 - WhatsApp delivery adapter

After deterministic templates, admin approval and delivery audit are stable, add WhatsApp transport.

Evolution API can be used here as a gateway adapter, but it should remain replaceable and disabled by default.

## Poller vs webhook

Use a poller first.

Reasons:

- no new public ingress;
- easier local development;
- simpler replay behavior;
- easier audit-first rollout;
- less security surface while the contract is still changing.

Consider webhooks later only after:

- authentication is defined;
- replay protection exists;
- event idempotency is documented;
- rate limits are configured;
- operational ownership is clear.

## Audit and privacy notes

Hermes events may include resident phone numbers and support intent metadata. They should be treated as operational personal data.

Do not store:

- CPF;
- CNPJ;
- Celesc credentials;
- consumer unit credentials;
- free-form LLM prompts from residents;
- raw sensitive support text unless a future retention policy allows it.

Payloads should stay minimal and structured.

## Acceptance checklist for issue #37

- ADR created in `docs/agent/decisions/`.
- Bootstrap proposal documented.
- User-facing guardrails defined.
- Explicit no-LLM-by-default decision documented.
- Initial integration strategy documented as poller-first.
- Evolution API relationship documented as gateway/adapter, not policy owner.
- No real WhatsApp delivery implemented.
- No PR #34 changes required.
