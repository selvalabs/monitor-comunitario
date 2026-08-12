# Member Access MVP

## Overview

The member access flow lets registered residents return to their alert panel without relying only on a browser-stored user ID.

This is an MVP access mechanism, not a full authentication system.

## Flow

```text
1. Resident fills the public registration form.
2. The API creates the user/address record.
3. The API generates a private access code.
4. The plain access code is returned only once in the registration response.
5. Only the access code hash is stored in the database.
6. Resident can later access /member with phone + access code.
```

## Endpoints

### `POST /users`

Creates a user and returns the one-time visible access code.

The response includes all public user fields plus:

```json
{
  "access_code": "ABCDE-23456"
}
```

The access code must be shown to the resident immediately after registration.

### `POST /member/access`

Validates member access with phone + access code.

Request:

```json
{
  "phone": "5548999999999",
  "access_code": "ABCDE-23456"
}
```

Successful response:

```json
{
  "user": {
    "id": 1,
    "name": "Resident",
    "phone": "5548999999999",
    "municipality": "Florianópolis"
  },
  "notifications": []
}
```

Invalid access returns `401 Unauthorized`.

## Member page

The resident page is available at:

```text
/member
```

After successful access, the backend creates a short-lived opaque session in Redis.
The browser receives the session only as an `HttpOnly`, `Secure`,
`SameSite=Strict` cookie. The member page restores its data through `GET /member/me`;
it does not store member data or credentials in `sessionStorage` or `localStorage`.

State-changing member operations require the readable CSRF cookie in the
`X-CSRF-Token` header. Logout uses `DELETE /member/session` and permanently
deletes the server-side session.

## Security notes

- The plain access code is never stored in the database.
- Existing user read endpoints do not expose `access_code` or `access_code_hash`.
- This MVP does not include recovery/reset flows yet.
- Existing users created before this migration do not automatically receive an access code.

## Future improvements

```text
magic link by email
access code by WhatsApp
Supabase Auth
code reset flow
member profile editing
stronger session model
```
