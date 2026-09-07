const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");

const src = readFileSync(require.resolve("../static/js/nav.js"), "utf8");

test("BEH-1: nav.js wires click listeners for all three nav ids", () => {
  for (const id of ["nav-incidents", "nav-escalations", "nav-directory"]) {
    assert.match(src, new RegExp(`getElementById\\("${id}"\\)`));
  }
  assert.match(src, /addEventListener\("click"/);
});

test("BEH-1: nav.js calls NavLogic's pure decision functions, never reimplements them", () => {
  assert.match(src, /NavLogic\.resolveActiveView/);
  assert.match(src, /NavLogic\.viewVisibility/);
});

test("BEH-1: showView toggles hidden and aria-current per the visibility map, no page reload", () => {
  assert.match(src, /\.hidden = /);
  assert.match(src, /setAttribute\("aria-current"/);
  assert.doesNotMatch(src, /location\.reload|location\.href\s*=/);
});

test("first activation dispatches to the corresponding screen loader", () => {
  assert.match(src, /loadEscalationsView\(/);
  assert.match(src, /loadDirectoryView\(/);
});
