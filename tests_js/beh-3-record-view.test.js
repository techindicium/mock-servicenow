const test = require("node:test");
const assert = require("node:assert/strict");
const { shapeIncidentRecordFields, formatNullableField } = require("../static/js/incident-logic.js");

const INCIDENT = {
  number: "TICKET-004417", account_id: "ACCOUNT-1001", category: "billing",
  short_description: "Invoice mismatch", description: "Customer reports a mismatch.",
  state: "new", priority: 2, opened_at: "2026-09-01T00:00:00Z", resolved_at: null,
  assigned_to: null, assignment_group: "Support Tier 1", escalated: false,
};

test("BEH-3: every field is present, including null fields as explicit placeholders", () => {
  const fields = shapeIncidentRecordFields(INCIDENT);
  const byLabel = Object.fromEntries(fields.map((f) => [f.label, f.value]));
  assert.equal(byLabel["Number"], "TICKET-004417");
  assert.equal(byLabel["Assigned to"], "Unassigned");
  assert.equal(byLabel["Resolved at"], "Not resolved");
  assert.equal(byLabel["Assignment group"], "Support Tier 1");
});

test("formatNullableField: null/undefined/empty all resolve to the placeholder", () => {
  assert.equal(formatNullableField(null, "Unassigned"), "Unassigned");
  assert.equal(formatNullableField(undefined, "Unassigned"), "Unassigned");
  assert.equal(formatNullableField("dana", "Unassigned"), "dana");
});
