const test = require("node:test");
const assert = require("node:assert/strict");
const { buildIncidentQueryParams } = require("../static/js/incident-logic.js");

test("BEH-2: includes only the filters that are set", () => {
  const params = buildIncidentQueryParams({ state: "new" }, 2, 25);
  assert.deepEqual(params, { state: "new", page: "2", page_size: "25" });
});

test("BEH-2: supports the full combination of state/category/account_id/escalated", () => {
  const params = buildIncidentQueryParams(
    { state: "in_progress", category: "billing", account_id: "ACCOUNT-1001", escalated: "true" },
    1, 50
  );
  assert.deepEqual(params, {
    state: "in_progress", category: "billing", account_id: "ACCOUNT-1001",
    escalated: "true", page: "1", page_size: "50",
  });
});

test("BEH-2: an empty-string filter value is omitted, not sent as a literal empty match", () => {
  const params = buildIncidentQueryParams({ state: "", category: "billing" }, 1, 50);
  assert.equal("state" in params, false);
  assert.equal(params.category, "billing");
});
