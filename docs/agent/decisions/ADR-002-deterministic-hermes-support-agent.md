# ADR-002 - Deterministic Hermes support agent

Date: 2026-07-24  
Status: Proposed  
Owner: SelvaLabs / Monitor Comunitario operator  
Issue: #37

## Context

Monitor Comunitario currently creates in-app notifications from public Celesc outage notices. The project also has an Evolution API adapter prepared behind feature flags, but real WhatsApp delivery is intentionally disabled until the operational setup is validated.

The next notification layer needs to support delivery, resident support, operational escalation and auditability without coupling the Monitor Comunitario backend to a specific WhatsApp gateway or to Jarbas internals.

Resident-facing communication has a higher safety requirement than internal operator summaries. Messages to residents can affect decisions about electricity outages, privacy requests and support expectations. For that reason, the resident-facing path must be deterministic by default.

## Decision

Create a dedicated Hermes agent boundary for notification, support and observability workflows.

Monitor Comunitario will emit auditable events and intents. Hermes will process those events and choose deterministic templates for resident-facing communication. LLM/provider calls are not allowed in resident-facing conversations by default.

The default resident flow is:

```text
resident message or notification event
-> deterministic classifier or explicit intent
-> approved template
-> audit record
-> delivery attempt or human escalation
-> no LLM/provider call
```

LLM/provider usage is reserved for internal/admin workflows only, such as:

- daily or weekly summaries for Frank;
- accumulated event triage;
- product improvement suggestions;
- operator-requested investigation support.

## Constraints

- Do not use LLM/provider calls in resident-facing support or notification flows by default.
- Do not send real WhatsApp messages in this phase.
- Do not configure real Telegram delivery in this phase.
- Do not create credentials, deploy services or expose public webhooks in this phase.
- Do not change PR #34 as part of this decision.
- Keep the current Evolution adapter disabled until operational validation exists.
- Keep resident data minimization aligned with `docs/LGPD.md` and `docs/agent/SECURITY.md`.

## Alternatives considered

### Keep Evolution API as the direct notification provider

This is simpler in the short term, but it puts transport too close to communication policy. It also does not provide a clear resident-support boundary or deterministic guardrails.

### Use Jarbas directly for resident support

This would reuse existing agent infrastructure, but it risks coupling Monitor Comunitario to a broader assistant surface. It also makes it easier for LLM behavior to leak into resident-facing flows.

### Add a dedicated Hermes boundary

This adds one explicit contract and audit layer, but keeps communication policy, escalation and delivery adapters separated from scraping, matching and persistence.

## Initial implementation boundary

The first technical bootstrap is internal only:

- deterministic intent/template catalog;
- `hermes_events` audit table;
- event lifecycle statuses;
- service for creating Hermes events;
- explicit block on `llm_allowed=True` for user-facing templates.

This bootstrap does not deliver WhatsApp messages, create Telegram messages, expose public webhooks or call LLM providers.

## User-facing guardrails

Resident-facing support and notification conversations are deterministic-only.

Required guardrails:

- use only approved templates;
- keep template keys versioned;
- never call LLM/provider from resident-facing flows by default;
- log every event and selected template;
- escalate unknown, privacy-sensitive or out-of-scope requests;
- keep Celesc disclaimers explicit;
- never present Monitor Comunitario as an official Celesc channel;
- do not request CPF, CNPJ, consumer unit credentials or Celesc account access.

## Allowed initial resident intents

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

## Initial templates

```text
explain_project_v1
not_official_celesc_v1
alert_explanation_v1
member_access_help_v1
lost_code_help_v1
update_address_help_v1
opt_out_received_v1
delete_data_request_received_v1
wrong_alert_feedback_received_v1
emergency_redirect_v1
out_of_scope_v1
human_escalation_v1
```

## Frank escalation events

Hermes should escalate operationally relevant events to Frank through the internal channel selected for operations, initially Telegram when configured:

```text
scraper_failed
parser_failed
worker_failed
zero_notices_unusual
many_uncertain_matches
notification_delivery_failed
admin_approval_pending
user_requested_removal
user_reported_wrong_alert
user_support_needs_human
privacy_sensitive_request
gateway_down
```

## Integration strategy

Start with a poller boundary instead of a public webhook.

Rationale:

- simpler to operate before public deployment;
- avoids exposing a new ingress surface too early;
- works with the current worker/API split;
- allows deterministic audit records before external delivery exists;
- keeps Hermes integration reversible while the event contract matures.

A webhook can be added later after authentication, replay protection, rate limits and operational ownership are defined.

## Evolution API relationship

Evolution API remains a gateway adapter, not the business decision layer.

Hermes owns communication policy, template selection, support guardrails and escalation decisions. Evolution may later be used by Hermes or by a delivery adapter as one WhatsApp transport option.

This decision makes Evolution:

- a possible future delivery gateway;
- replaceable by another WhatsApp provider;
- isolated from resident-support policy;
- disabled until credentials, instance health, delivery status and retry behavior are validated.

## Consequences

Positive:

- resident-facing behavior is safer and easier to audit;
- Hermes can evolve without changing parser/matcher internals;
- operational escalation has a clear boundary;
- LLM usage is explicitly kept away from residents by default;
- WhatsApp transport remains replaceable.

Negative:

- adds a new event contract and table;
- requires clear ownership of Hermes processing later;
- needs future retry/delivery-state design before real WhatsApp usage;
- creates documentation and process overhead before shipping external messages.

## Review trigger

Review this ADR before any of these changes:

- enabling real WhatsApp or Telegram delivery;
- adding a public webhook;
- allowing any LLM/provider output into resident-facing communication;
- changing retention rules for Hermes event payloads;
- replacing Evolution API with another WhatsApp gateway;
- merging Hermes processing into the main API process.

## Follow-up work

- Add admin read endpoints for `hermes_events`.
- Connect notification creation to `notification_ready` Hermes events.
- Add a local Hermes poller command.
- Add delivery status transitions and retry policy.
- Add Telegram escalation adapter behind configuration.
- Add WhatsApp gateway integration only after deterministic templates and delivery audit are validated.
- Keep PR #34 independent from this architecture track.

## Links

- Issue: https://github.com/selvalabs/monitor-comunitario/issues/37
- Branch: https://github.com/selvalabs/monitor-comunitario/tree/hermes-events-bootstrap
- Compare: https://github.com/selvalabs/monitor-comunitario/compare/main...hermes-events-bootstrap
- Related docs: `docs/agent/hermes-bootstrap.md`, `docs/ARCHITECTURE.md`, `docs/PRD.md`
