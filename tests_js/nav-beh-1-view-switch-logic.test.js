const test = require("node:test");
const assert = require("node:assert/strict");
const {
  NAV_VIEWS,
  DEFAULT_VIEW,
  isKnownView,
  resolveActiveView,
  viewVisibility,
} = require("../static/js/nav-logic.js");

test("BEH-1: Incidents is the default active view", () => {
  assert.equal(DEFAULT_VIEW, "incidents");
  assert.deepEqual(NAV_VIEWS, ["incidents", "escalations", "directory"]);
});

test("BEH-1: exactly one view is visible for each known nav target", () => {
  for (const view of NAV_VIEWS) {
    const visibility = viewVisibility(view);
    assert.equal(Object.values(visibility).filter(Boolean).length, 1);
    assert.equal(visibility[view], true);
  }
});

test("BEH-1: an unrecognized target is a defensive no-op, staying on the current view", () => {
  assert.equal(resolveActiveView("kanban", "escalations"), "escalations");
  assert.equal(resolveActiveView("kanban", undefined), DEFAULT_VIEW);
});

test("BEH-1: a known target always becomes active", () => {
  assert.equal(resolveActiveView("directory", "incidents"), "directory");
  assert.equal(resolveActiveView("incidents", "directory"), "incidents");
});

test("isKnownView recognizes exactly the three nav targets", () => {
  assert.equal(isKnownView("incidents"), true);
  assert.equal(isKnownView("escalations"), true);
  assert.equal(isKnownView("directory"), true);
  assert.equal(isKnownView("kanban"), false);
  assert.equal(isKnownView(undefined), false);
});
