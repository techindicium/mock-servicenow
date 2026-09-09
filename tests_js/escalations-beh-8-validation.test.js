const test = require("node:test");
const assert = require("node:assert/strict");
const { validateCreateEscalationForm } = require("../static/js/escalations-logic.js");

test("BEH-8: missing account_id is flagged", () => {
  const { valid, errors } = validateCreateEscalationForm({ account_id: "", summary: "New issue" });
  assert.equal(valid, false);
  assert.equal(errors.account_id, "account_id is required");
});

test("BEH-8: missing summary is flagged", () => {
  const { valid, errors } = validateCreateEscalationForm({ account_id: "ACCOUNT-1001", summary: "" });
  assert.equal(valid, false);
  assert.equal(errors.summary, "summary is required");
});

test("BEH-8: both fields present is valid", () => {
  const { valid, errors } = validateCreateEscalationForm({ account_id: "ACCOUNT-1001", summary: "New issue" });
  assert.equal(valid, true);
  assert.deepEqual(errors, {});
});
