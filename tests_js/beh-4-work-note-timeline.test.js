const test = require("node:test");
const assert = require("node:assert/strict");
const { sortWorkNotesChronological } = require("../static/js/incident-logic.js");

test("BEH-4: sorts notes ascending by created_at regardless of input order", () => {
  const notes = [
    { sys_id: "INTERACTION-0000002", created_at: "2026-09-02T00:00:00Z" },
    { sys_id: "INTERACTION-0000001", created_at: "2026-09-01T00:00:00Z" },
  ];
  const sorted = sortWorkNotesChronological(notes);
  assert.deepEqual(sorted.map((n) => n.sys_id), ["INTERACTION-0000001", "INTERACTION-0000002"]);
});

test("BEH-4: does not mutate the input array", () => {
  const notes = [{ created_at: "b" }, { created_at: "a" }];
  const copy = [...notes];
  sortWorkNotesChronological(notes);
  assert.deepEqual(notes, copy);
});

test("BEH-4: handles zero notes without error", () => {
  assert.deepEqual(sortWorkNotesChronological([]), []);
});
