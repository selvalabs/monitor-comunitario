# Soberania Email Ingress Worker

Thin Cloudflare Email Service ingress for explicit agent addresses.

## Local validation

```bash
npm test
```

## Configure secrets

```bash
npx wrangler secret put EMAIL_INGRESS_SECRET
```

`EMAIL_INGRESS_URL`, `ALLOWED_RECIPIENTS`, and `MAX_RAW_BYTES` are non-secret vars in `wrangler.jsonc`.

The Worker does not parse, execute, or reason over email content. It forwards bounded raw MIME to the authenticated backend with an HMAC signature and idempotency key. Keep catch-all routing disabled until the backend is deployed and tested.


## Security boundary

This Worker has no public HTTP API. Its `fetch` handler returns `404`; the supported entry point is Cloudflare Email Service only.

The backend endpoint must be reachable only through the Monitor-specific Cloudflare Tunnel and must reject requests unless all of the following are true:

- `X-Email-Ingress-Signature` matches `HMAC-SHA256(EMAIL_INGRESS_SECRET, timestamp + "." + raw_body)` using constant-time comparison;
- `X-Email-Ingress-Timestamp` is an ISO-8601 timestamp within five minutes of server time;
- `Idempotency-Key` is present and has not already been accepted;
- the JSON envelope is version `1`, the recipient is allowlisted, and the decoded MIME size is within the backend limit.

The Tunnel is an additional network boundary, not a replacement for HMAC verification. Do not configure a catch-all email rule, expose the backend port directly, or log the raw MIME payload.
