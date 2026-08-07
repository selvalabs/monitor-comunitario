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
