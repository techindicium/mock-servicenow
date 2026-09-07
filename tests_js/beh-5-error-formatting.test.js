const test = require("node:test");
const assert = require("node:assert/strict");
const { formatApiError, escalationNotFoundMessage } = require("../static/js/ui-errors.js");

test("BEH-5: a network error (no status) names the failed action", () => {
  const msg = formatApiError("Loading escalations", {});
  assert.match(msg, /Loading escalations/);
  assert.match(msg, /network error/i);
});

test("BEH-5: a non-2xx response names the failed action and status, never a blank message", () => {
  const msg = formatApiError("Saving escalation", { status: 500 });
  assert.match(msg, /Saving escalation/);
  assert.match(msg, /500/);
});

test("Error Cases table: a 404 on PATCH /escalations/{number} names it as an escalation-not-found state", () => {
  const msg = escalationNotFoundMessage("ESCALATION-9999");
  assert.match(msg, /ESCALATION-9999/);
  assert.match(msg, /not found/i);
});
