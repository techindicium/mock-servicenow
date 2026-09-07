const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");

const html = readFileSync(require.resolve("../static/index.html"), "utf8");

test("BEH-1: nav rail exists with three nav items, Incidents active by default", () => {
  assert.match(html, /<nav class="nav-rail"/);
  assert.match(
    html,
    /<button type="button" class="nav-item active" id="nav-incidents" data-view="incidents"[^>]*>Incidents<\/button>/
  );
  assert.match(
    html,
    /<button type="button" class="nav-item" id="nav-escalations" data-view="escalations">Escalations<\/button>/
  );
  assert.match(
    html,
    /<button type="button" class="nav-item" id="nav-directory" data-view="directory">Directory<\/button>/
  );
});

test("Postconditions: existing Incidents skeleton is relocated, not renamed", () => {
  assert.match(html, /<section id="view-incidents" class="view">/);
});

test("BEH-1: Escalations/Directory view containers exist, hidden by default", () => {
  assert.match(html, /<section id="view-escalations" class="view" hidden>/);
  assert.match(html, /<section id="view-directory" class="view" hidden>/);
});

test("new stylesheet and scripts are wired in", () => {
  assert.match(html, /<link rel="stylesheet" href="\/static\/css\/nav\.css">/);
  assert.match(html, /<script src="\/static\/js\/nav-logic\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/nav\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/escalations-logic\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/escalations\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/directory-logic\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/directory\.js"><\/script>/);
});
