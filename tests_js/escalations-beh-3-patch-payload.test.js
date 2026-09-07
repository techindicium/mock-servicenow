const test = require("node:test");
const assert = require("node:assert/strict");
const { buildEscalationPatchPayload } = require("../static/js/escalations-logic.js");

const original = { summary: "Renewal at risk", owner: "Rui Bastos", closed_at: null };

test("BEH-3: only changed fields are sent", () => {
  const payload = buildEscalationPatchPayload(original, { summary: "Renewal at risk", owner: "Rui Bastos", closed_at: null });
  assert.deepEqual(payload, {});

  const payload2 = buildEscalationPatchPayload(original, { summary: "Escalated to VP", owner: "Rui Bastos", closed_at: null });
  assert.deepEqual(payload2, { summary: "Escalated to VP" });
});

test("BEH-3: explicitly blanking owner sends an explicit null, not an omission", () => {
  const payload = buildEscalationPatchPayload(original, { summary: "Renewal at risk", owner: "", closed_at: null });
  assert.deepEqual(payload, { owner: null });
});

test("BEH-3: setting closed_at sends the new value", () => {
  const payload = buildEscalationPatchPayload(original, { summary: "Renewal at risk", owner: "Rui Bastos", closed_at: "2026-03-01T00:00:00Z" });
  assert.deepEqual(payload, { closed_at: "2026-03-01T00:00:00Z" });
});
