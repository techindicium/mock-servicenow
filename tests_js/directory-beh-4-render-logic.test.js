const test = require("node:test");
const assert = require("node:assert/strict");
const { userRowCells, groupRowCells } = require("../static/js/directory-logic.js");

test("BEH-4: user row cells include name/role/assignment_group", () => {
  const cells = userRowCells({ name: "Rui Bastos", role: "Support Manager", assignment_group: null });
  assert.equal(cells.name, "Rui Bastos");
  assert.equal(cells.role, "Support Manager");
  assert.equal(cells.assignment_group, "");
});

test("BEH-4: a grouped user's assignment_group passes through unchanged", () => {
  const cells = userRowCells({ name: "Joao Pinto", role: "Support Engineer", assignment_group: "Support Tier 1" });
  assert.equal(cells.assignment_group, "Support Tier 1");
});

test("BEH-4: group row cells expose only name", () => {
  const cells = groupRowCells({ name: "Support Tier 1" });
  assert.deepEqual(cells, { name: "Support Tier 1" });
});
