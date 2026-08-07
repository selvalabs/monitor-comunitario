import test from "node:test";
import assert from "node:assert/strict";
import { allowedRecipient } from "../src/index.js";

test("allows only explicitly configured recipients", () => {
  assert.equal(
    allowedRecipient("Monitor@Soberania.cloud", "monitor@soberania.cloud"),
    true,
  );
  assert.equal(allowedRecipient("other@soberania.cloud", "monitor@soberania.cloud"), false);
  assert.equal(allowedRecipient("monitor@soberania.cloud", ""), false);
});
