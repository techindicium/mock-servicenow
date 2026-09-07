const test = require("node:test");
const assert = require("node:assert/strict");
const { shapeSlaRows } = require("../static/js/incident-logic.js");

test("BEH-6: every field is passed through unchanged, plus a breach-flag class", () => {
  const rows = shapeSlaRows([
    { sys_id: "SLA-0001", incident_number: "TICKET-004417", sla_definition: "first_response",
      target_minutes: 30, actual_minutes: 45, has_breached: true, business_time_only: false },
  ]);
  assert.equal(rows[0].sla_definition, "first_response");
  assert.equal(rows[0].actual_minutes, 45);
  assert.equal(rows[0].breachClass, "sla-breached");
});

test("BEH-6: a non-breached row gets no breach-flag class, factually — not hidden either way", () => {
  const rows = shapeSlaRows([
    { sys_id: "SLA-0002", has_breached: false, target_minutes: 240, actual_minutes: 120,
      sla_definition: "resolution", business_time_only: true, incident_number: "TICKET-004417" },
  ]);
  assert.equal(rows[0].breachClass, "");
});

test("BEH-6: never omits or filters any row — this is data shaping, not a block/allow decision", () => {
  const rows = shapeSlaRows([{ has_breached: true }, { has_breached: false }]);
  assert.equal(rows.length, 2);
});

test("BEH-6: an empty/missing input yields an empty array, not a crash", () => {
  assert.deepEqual(shapeSlaRows(undefined), []);
});
