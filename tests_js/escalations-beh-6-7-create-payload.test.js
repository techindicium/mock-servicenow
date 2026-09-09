const test = require("node:test");
const assert = require("node:assert/strict");
const { buildEscalationCreatePayload } = require("../static/js/escalations-logic.js");

test("BEH-6: required-only fields produce a minimal payload", () => {
  const payload = buildEscalationCreatePayload({ account_id: "ACCOUNT-1001", summary: "New issue", incident_number: "", owner: "" });
  assert.deepEqual(payload, { account_id: "ACCOUNT-1001", summary: "New issue" });
});

test("BEH-7: optional fields are included when filled in", () => {
  const payload = buildEscalationCreatePayload({ account_id: "ACCOUNT-1001", summary: "New issue", incident_number: "TICKET-004417", owner: "Rui Bastos" });
  assert.deepEqual(payload, { account_id: "ACCOUNT-1001", summary: "New issue", incident_number: "TICKET-004417", owner: "Rui Bastos" });
});
