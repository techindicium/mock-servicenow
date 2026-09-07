const test = require("node:test");
const assert = require("node:assert/strict");
const { OWNER_UNASSIGNED_LABEL, displayOwner, escalationRowCells } =
  require("../static/js/escalations-logic.js");

test("BEH-2: owner: null renders as an explicit Unassigned state", () => {
  assert.equal(displayOwner(null), OWNER_UNASSIGNED_LABEL);
  assert.equal(displayOwner(undefined), OWNER_UNASSIGNED_LABEL);
  assert.equal(displayOwner("Rui Bastos"), "Rui Bastos");
});

test("BEH-2: row cells include number/account_id/summary/opened_at/closed_at/owner, never incident_number", () => {
  const cells = escalationRowCells({
    number: "ESCALATION-0001",
    incident_number: "INC0000123",
    account_id: "ACC-1",
    summary: "Renewal at risk",
    opened_at: "2026-01-01T00:00:00Z",
    closed_at: null,
    owner: null,
  });
  assert.equal(cells.number, "ESCALATION-0001");
  assert.equal(cells.account_id, "ACC-1");
  assert.equal(cells.summary, "Renewal at risk");
  assert.equal(cells.owner, "Unassigned");
  assert.equal(cells.ownerIsUnassigned, true);
  assert.equal("incident_number" in cells, false);
});

test("BEH-2: an owned, closed escalation renders its real values, not placeholders", () => {
  const cells = escalationRowCells({
    number: "ESCALATION-0002",
    account_id: "ACC-2",
    summary: "SLA dispute",
    opened_at: "2026-01-01T00:00:00Z",
    closed_at: "2026-02-01T00:00:00Z",
    owner: "Priya Nair",
  });
  assert.equal(cells.owner, "Priya Nair");
  assert.equal(cells.ownerIsUnassigned, false);
  assert.equal(cells.closed_at, "2026-02-01T00:00:00Z");
});
