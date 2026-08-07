const DEFAULT_MAX_RAW_BYTES = 10 * 1024 * 1024;

function normalizeAddress(value) {
  return String(value || "").trim().toLowerCase();
}

export function allowedRecipient(recipient, allowlist) {
  const address = normalizeAddress(recipient);
  const allowed = String(allowlist || "")
    .split(",")
    .map(normalizeAddress)
    .filter(Boolean);
  return Boolean(address) && allowed.includes(address);
}

export function hexEncode(bytes) {
  return [...new Uint8Array(bytes)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return hexEncode(digest);
}

async function hmacSha256Hex(secret, value) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return hexEncode(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
}

async function readLimitedRaw(stream, maxBytes) {
  const reader = stream.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) throw new Error("email_too_large");
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const result = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return result;
}

function base64Encode(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}

async function postEnvelope(env, envelope, timestamp) {
  const body = JSON.stringify(envelope);
  const signature = await hmacSha256Hex(env.EMAIL_INGRESS_SECRET, `${timestamp}.${body}`);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    return await fetch(env.EMAIL_INGRESS_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-email-ingress-timestamp": timestamp,
        "x-email-ingress-signature": `sha256=${signature}`,
        "idempotency-key": envelope.idempotencyKey,
      },
      body,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

export default {
  async email(message, env) {
    if (!env.EMAIL_INGRESS_SECRET || !env.EMAIL_INGRESS_URL) {
      message.reject("email ingress is not configured");
      return;
    }

    const recipient = normalizeAddress(message.to);
    if (!allowedRecipient(recipient, env.ALLOWED_RECIPIENTS)) {
      message.reject("recipient is not configured");
      return;
    }

    const maxBytes = Number(env.MAX_RAW_BYTES || DEFAULT_MAX_RAW_BYTES);
    let raw;
    try {
      raw = await readLimitedRaw(message.raw, maxBytes);
    } catch (error) {
      message.reject(error instanceof Error && error.message === "email_too_large" ? "email is too large" : "invalid email");
      return;
    }

    const rawMimeBase64 = base64Encode(raw);
    const idempotencyKey = await sha256Hex(`${recipient}
${rawMimeBase64}`);
    const receivedAt = new Date().toISOString();
    const envelope = {
      version: 1,
      idempotencyKey,
      recipient,
      sender: normalizeAddress(message.from),
      receivedAt,
      rawMimeBase64,
    };
    const response = await postEnvelope(env, envelope, receivedAt);
    if (!response.ok) {
      message.reject("email ingress temporarily unavailable");
    }
  },

  async fetch() {
    return new Response("email ingress worker", { status: 200 });
  },
};
