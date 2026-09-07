const test = require("node:test");
const assert = require("node:assert/strict");
const { diffIncidentFields } = require("../static/js/incident-logic.js");

const ORIGINAL = {
  number: "TICKET-004417", state: "in_progress", priority: 2,
  assigned_to: null, assignment_group: "Support Tier 1",
};

test("BEH-7: diffs only the fields that actually changed", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, state: "resolved" });
  assert.deepEqual(patch, { state: "resolved" });
});

test("BEH-7: an edited form with no actual change produces an empty patch", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL });
  assert.deepEqual(patch, {});
});

test("BEH-7: priority is compared numerically, not as a select's string value", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, priority: "4" });
  assert.deepEqual(patch, { priority: 4 });
});

test("BEH-7: an emptied assigned_to/assignment_group diffs to null, not an empty string", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, assignment_group: "" });
  assert.deepEqual(patch, { assignment_group: null });
});

test("BEH-7 [no-guard regression]: resolving with an open first_response breach diffs and "
  + "submits identically to any other state change — no field is added, removed, or annotated",
  () => {
    // This UI has no SLA data at diff time (SLA rows are a separate fetch — see Task 5) and
    // diffIncidentFields never inspects them even by accident: same shape whether or not a
    // breach exists, because the function only ever compares the four patchable fields.
    const patch = diffIncidentFields(
      { ...ORIGINAL, state: "in_progress" },
      { ...ORIGINAL, state: "resolved" }
    );
    assert.deepEqual(Object.keys(patch), ["state"]);
    assert.equal(patch.state, "resolved");
  }
);

test("BEH-7: number/account_id/opened_at are never patchable fields, even if present on the object", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, number: "TICKET-999999", state: "closed" });
  assert.equal("number" in patch, false);
  assert.deepEqual(patch, { state: "closed" });
});
