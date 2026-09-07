const test = require("node:test");
const assert = require("node:assert/strict");
const { validateCreateIncidentForm } = require("../static/js/incident-logic.js");

const VALID = {
  account_id: "ACCOUNT-1001", category: "billing", short_description: "Invoice mismatch",
  description: "Customer reports a mismatch.", state: "new", priority: "2",
};

test("BEH-8: all six required fields present passes validation", () => {
  assert.equal(validateCreateIncidentForm(VALID).valid, true);
});

for (const missing of Object.keys(VALID)) {
  test(`BEH-8: missing ${missing} fails validation and names the field`, () => {
    const fields = { ...VALID, [missing]: "" };
    const result = validateCreateIncidentForm(fields);
    assert.equal(result.valid, false);
    assert.ok(result.errors[missing]);
  });
}

test("BEH-8: category has no fixed enum at this layer — any non-empty value passes", () => {
  const result = validateCreateIncidentForm({ ...VALID, category: "anything-goes" });
  assert.equal(result.valid, true);
});
