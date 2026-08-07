import test from "node:test";
import assert from "node:assert/strict";
import worker, { allowedRecipient } from "../src/index.js";

test("allows only explicitly configured recipients", () => {
  assert.equal(
    allowedRecipient("Monitor@Soberania.cloud", "monitor@soberania.cloud"),
    true,
  );
  assert.equal(allowedRecipient("other@soberania.cloud", "monitor@soberania.cloud"), false);
  assert.equal(allowedRecipient("monitor@soberania.cloud", ""), false);
});


test("does not expose a public HTTP endpoint", async () => {
  const response = await worker.fetch(new Request("https://monitorcomunitario.soberania.cloud/"));
  assert.equal(response.status, 404);
  assert.equal(await response.text(), "");
});
