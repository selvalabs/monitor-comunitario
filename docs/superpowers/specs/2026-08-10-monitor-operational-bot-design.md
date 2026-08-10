# Monitor Operational Bot Design

Date: 2026-08-10
Issue: #124
Status: Proposed

## Goal

Make the Monitor Telegram bot the operational control plane for the Monitor Comunitario app. The bot must execute the app's existing administrative workflows through an authenticated internal API, while the API and workers retain ownership of authorization, persistence, queues, provider credentials, and audit records.

The mailbox is one operational module, not the bot's primary purpose.

## Boundaries

- Telegram bot: command parsing, explicit confirmations, previews, and operator feedback.
- Monitor API: authorization, validation, rate limits, state transitions, and audit records.
- Monitor workers: scraping, queue consumption, retries, and provider calls.
- Brevo: email delivery only; its REST key never reaches Telegram or the bot process.
- Hermes: WhatsApp delivery and phone-confirmation callback remain owned by Hermes.
- PostgreSQL: system of record for users, events, notifications, mailbox messages, threads, jobs, and audit records.

## Authentication and authorization

The bot uses a dedicated internal service credential, separate from `ADMIN_API_KEY`, Hermes secrets, Brevo keys, and Telegram credentials. The API accepts it only on private internal routes. Every mutating operation records the Telegram user ID, chat ID, topic ID when present, action, target, outcome, and timestamp.

Destructive or externally visible actions require a confirmation token bound transactionally to the Telegram user, chat, topic, action, target, and short expiry. The bot never infers approval from a later or unrelated Telegram message.

## Operational workflows

### Registration and confirmation

The public app remains the source of registration. It sends the first email OTP through the configured email provider. The bot can:

- list pending registrations without exposing OTP values;
- show email verification status and provider delivery ID in shortened form;
- resend only the approved confirmation template, with rate limits;
- show the current WhatsApp confirmation event state;
- retry a failed Hermes event when retry policy allows it;
- cancel an expired or explicitly rejected pending registration.

The bot cannot send arbitrary recipient emails from this flow.

### Users

- list active or inactive users with bounded pagination;
- inspect one user with privacy-minimized fields;
- update only fields approved by the API contract;
- approve or disable notifications with explicit confirmation;
- deactivate a user with explicit confirmation;
- inspect the user's notification and confirmation history.

### Monitoring

- report API, database, Redis, worker, scheduler, and last-run health;
- trigger one manual monitoring run after confirmation;
- list runs with status, counts, and bounded error summaries;
- inspect one run and its snapshot reference without exposing private filesystem data.

### Notifications and Hermes events

- list pending, failed, processed, and escalated notifications/events;
- inspect an event payload with sensitive fields redacted;
- retry only retryable failures;
- mark an event resolved or escalated through the existing audited state machine.

The bot never fabricates a delivery success. Provider acceptance and final delivery remain distinct states.

### Mailbox

- list received messages with pagination;
- inspect parsed sender, recipients, subject, timestamp, body, and attachment metadata;
- preserve and expose quoted history without treating it as the current reply;
- mark a message processed or ignored with audit;
- create a response draft from a message or thread;
- render a complete preview before sending;
- send only after a valid confirmation token is consumed.

Mailbox parsing stores `Message-ID`, `In-Reply-To`, and `References` and resolves threads deterministically. Raw MIME remains protected and is never written to Telegram logs.

## Command surface

The initial command set is:

```text
/status
/run
/runs
/pending
/resend-confirmation USER_ID
/email-status USER_ID
/users
/user USER_ID
/approve USER_ID CONFIRM
/disable USER_ID CONFIRM
/notifications
/events
/retry-event EVENT_ID CONFIRM
/mailbox
/mail MESSAGE_ID
/reply MESSAGE_ID
/confirm NONCE
/cancel NONCE
```

Commands return short summaries and stable technical IDs. Full bodies are shown only through the approved mailbox view and are escaped for Telegram formatting.

## Data and queues

The implementation adds normalized mailbox messages, threads, attachment metadata, outbound drafts, delivery events, approval nonce hashes, and a durable jobs table or compatible existing queue abstraction. Inserts and claims are idempotent. Queue consumers use `FOR UPDATE SKIP LOCKED`, bounded exponential retry, and a dead-letter state.

Brevo I/O runs outside database locks. A 2xx response without a provider `messageId` is ambiguous and cannot be marked sent. Brevo webhook events are authenticated, deduplicated, and map to delivery states.

## Error handling

- Invalid command or missing target: return a safe usage message.
- Unauthorized Telegram user: reject without revealing operational data.
- Expired/replayed nonce: reject and record only a redacted audit result.
- Provider timeout: mark ambiguous, reconcile before retrying.
- Permanent provider 4xx: mark failed with a redacted reason.
- Queue exhaustion: dead-letter and notify the operator.

## Validation

Tests must cover command authorization, nonce binding and replay, registration resend limits, user mutations, manual-run authorization, event retry policy, MIME parsing, thread resolution, Telegram escaping/chunking, queue idempotency, Brevo `messageId` handling, webhook authentication/deduplication, and Compose contracts.

Production validation requires a private backup, scoped deployment, rollback command, health checks, a signed MIME smoke test, a real registration email test, an approved Telegram action, and provider webhook evidence.

## Rollout order

1. Add internal API authentication and audited bot operations.
2. Implement registration status and approved OTP resend.
3. Add users, notifications, monitoring runs, and Hermes event operations.
4. Add normalized mailbox parsing and thread storage.
5. Add draft, approval, Brevo sender worker, and delivery webhook.
6. Deploy each slice independently with focused smoke tests.
