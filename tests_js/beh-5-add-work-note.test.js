const test = require("node:test");
const assert = require("node:assert/strict");
const { validateWorkNoteForm, NOTE_TYPES } = require("../static/js/incident-logic.js");

test("BEH-5: all three fields required, none constrained beyond note_type's enum", () => {
  const result = validateWorkNoteForm({ created_by: "", note_type: "comment", body: "hi" });
  assert.equal(result.valid, false);
  assert.ok(result.errors.created_by);
});

test("BEH-5: created_by accepts any free-text value, including 'assist' or 'customer'", () => {
  for (const author of ["assist", "customer", "any-agent-name"]) {
    const result = validateWorkNoteForm({ created_by: author, note_type: "comment", body: "hi" });
    assert.equal(result.valid, true, `expected ${author} to be accepted`);
  }
});

test("BEH-5: note_type must be one of the four fixed values", () => {
  const result = validateWorkNoteForm({ created_by: "assist", note_type: "not-real", body: "hi" });
  assert.equal(result.valid, false);
  assert.ok(result.errors.note_type);
});

test("NOTE_TYPES matches the four values the API validates against", () => {
  assert.deepEqual(NOTE_TYPES, ["comment", "work_note", "state_change", "proposal_sent"]);
});

test("BEH-5: a fully valid form has no errors", () => {
  const result = validateWorkNoteForm({ created_by: "assist", note_type: "work_note", body: "Called customer." });
  assert.deepEqual(result.errors, {});
});
