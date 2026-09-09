const test = require("node:test");
const assert = require("node:assert/strict");
const { shapeRelatedEscalation } = require("../static/js/incident-logic.js");

const ESCALATIONS = [
  {
    number: "ESCALATION-0409", incident_number: null, account_id: "ACCOUNT-1003",
    summary: "Cold chain temperature export missing rows",
    opened_at: "2026-07-05T00:00:00Z", closed_at: null, owner: "Priya Nair",
  },
  {
    number: "ESCALATION-0412", incident_number: "TICKET-004401", account_id: "ACCOUNT-1001",
    summary: "EDI feed rejecting with E-114, root cause not identified",
    opened_at: "2026-07-13T00:00:00Z", closed_at: null, owner: null,
  },
  {
    number: "ESCALATION-0415", incident_number: "TICKET-004401", account_id: "ACCOUNT-1008",
    summary: "A second, later escalation on the same incident",
    opened_at: "2026-07-21T00:00:00Z", closed_at: "2026-08-01T00:00:00Z", owner: "Joao Pinto",
  },
];

test("BEH-10: no match returns null", () => {
  assert.equal(shapeRelatedEscalation(ESCALATIONS, "TICKET-999999"), null);
});

test("BEH-10: a single match is shaped with real values", () => {
  const result = shapeRelatedEscalation(
    [ESCALATIONS[0], ESCALATIONS[1]], "TICKET-004401"
  );
  assert.equal(result.number, "ESCALATION-0412");
  assert.equal(result.summary, "EDI feed rejecting with E-114, root cause not identified");
});

test("BEH-10: null owner renders as an explicit unassigned state", () => {
  const result = shapeRelatedEscalation([ESCALATIONS[1]], "TICKET-004401");
  assert.equal(result.owner, "unassigned");
});

test("BEH-10: null closed_at renders as an explicit Open state", () => {
  const result = shapeRelatedEscalation([ESCALATIONS[1]], "TICKET-004401");
  assert.equal(result.closed_at, "Open");
});

test("BEH-10: a real, non-null owner/closed_at pass through unchanged", () => {
  const result = shapeRelatedEscalation([ESCALATIONS[2]], "TICKET-004401");
  assert.equal(result.owner, "Joao Pinto");
  assert.equal(result.closed_at, "2026-08-01T00:00:00Z");
});

test("BEH-10: multiple matches resolve to the first by number ascending", () => {
  const result = shapeRelatedEscalation(ESCALATIONS, "TICKET-004401");
  assert.equal(result.number, "ESCALATION-0412"); // 0412 < 0415
});

test("BEH-10: an empty or missing escalations array is a no-match, not a crash", () => {
  assert.equal(shapeRelatedEscalation([], "TICKET-004401"), null);
  assert.equal(shapeRelatedEscalation(undefined, "TICKET-004401"), null);
});
