const test = require("node:test");
const assert = require("node:assert/strict");
const { formatFetchError } = require("../static/js/incident-logic.js");

test("BEH-9: names the failed action and the server message on an HTTP error", () => {
  const msg = formatFetchError("Loading incidents", { status: 500, message: "boom" });
  assert.match(msg, /Loading incidents/);
  assert.match(msg, /500/);
  assert.match(msg, /boom/);
});

test("BEH-9: falls back to a network-error message with no status", () => {
  const msg = formatFetchError("Loading incidents", { message: "Failed to fetch" });
  assert.match(msg, /Loading incidents/);
  assert.match(msg, /Failed to fetch/);
});

test("BEH-9: never returns an empty message even with a bare error", () => {
  const msg = formatFetchError("Loading incidents", {});
  assert.ok(msg && msg.length > 0);
});

test("BEH-9: a 422 message surfaces the API's own field-naming text verbatim", () => {
  const msg = formatFetchError("Saving incident", {
    status: 422, message: "state must be one of: new, in_progress, on_hold, resolved, closed",
  });
  assert.match(msg, /state must be one of/);
});
