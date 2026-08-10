# Monitor Operational Bot Design

Date: 2026-08-10
Issue: #124
Status: Proposed

## Goal

Make the Monitor Telegram bot the operational control plane for the Monitor Comunitario app administrator. The bot must execute only the app's administrative workflows through an authenticated internal API, while the API and workers retain ownership of authorization, persistence, queues, provider credentials, and audit records.

The bot is a narrow operational control surface, not a general mailbox or admin dashboard.

## Boundaries

- Telegram bot: command parsing, explicit confirmations, previews, and operator feedback.
- Monitor API: authorization, validation, rate limits, state transitions, and audit records.
- Monitor workers: scraping, queue consumption, retries, and provider calls.
- Brevo: email delivery only; its REST key never reaches Telegram or the bot process.
- Hermes: WhatsApp delivery and phone-confirmation callback remain owned by Hermes.
- PostgreSQL: system of record for users, registration events, notifications, and audit records.

## Authentication and authorization

The bot uses a dedicated internal service credential, separate from `ADMIN_API_KEY`, Hermes secrets, Brevo keys, and Telegram credentials. The API accepts it only on private internal routes. Every mutating operation records the Telegram user ID, chat ID, topic ID when present, action, target, outcome, and timestamp.

Destructive or externally visible actions require a confirmation token bound transactionally to the Telegram user, chat, topic, action, target, and short expiry. The bot never infers approval from a later or unrelated Telegram message.

## Operational workflow

### Registration and member-access support

The public app remains the only source of resident registration and resident confirmation. The bot does not execute the resident flow. It can perform limited administrative support actions:

- list pending registrations without exposing OTP values;
- show email verification status and provider delivery ID in shortened form;
- resend only the approved confirmation template, with rate limits;
- show the current WhatsApp confirmation event state;
- retry a failed Hermes event when retry policy allows it;
- cancel an expired or explicitly rejected pending registration.

The bot cannot create a resident, verify an OTP, answer `OK` or `CANCELAR` on behalf of a resident, generate or expose a resident access code, alter resident consent, access the member area, or send arbitrary recipient emails.

The bot may inspect only the registration state and the related approved Hermes events. It does not become a general admin dashboard, monitoring console, notification manager, or email client.

## Command surface

The initial command set is:

```text
/status
/pending
/resend-confirmation EMAIL
/email-status EMAIL
/events
/retry-event EVENT_ID CONFIRM
/confirm NONCE
/cancel NONCE
```

Commands return short summaries and stable technical IDs. The bot never exposes resident access codes, OTP values, full registration payloads, or arbitrary message bodies.

## Data and queues

The implementation reuses the existing Redis pending-registration store and
Hermes event table. It adds only the metadata needed to audit email delivery
and enforce resend cooldowns. The OTP hash, recipient address, and expiry
remain in the protected backend store; the Telegram bot receives status and
provider identifiers only.

## Error handling

- Invalid command or missing target: return a safe usage message.
- Unauthorized Telegram user: reject without revealing operational data.
- Expired/replayed nonce: reject and record only a redacted audit result.
- Provider timeout: mark ambiguous, reconcile before retrying.
- Permanent provider 4xx: mark failed with a redacted reason.
- Queue exhaustion: dead-letter and notify the operator.

## Validation

Tests must cover command authorization, nonce binding and replay, pending-registration listing, OTP resend limits, OTP redaction, Hermes event retry policy, Brevo `messageId` handling, and the existing resident email/WhatsApp confirmation flow.

Production validation requires a private backup, scoped deployment, rollback command, health checks, a signed MIME smoke test, a real registration email test, an approved Telegram action, and provider webhook evidence.

## Rollout order

1. Add internal API authentication and audited bot operations.
2. Implement registration status and approved OTP resend.
3. Add Hermes event status and retry operations limited to registration events.
4. Connect the Telegram command adapter to these private endpoints.
5. Deploy the registration-support slice with focused smoke tests.
