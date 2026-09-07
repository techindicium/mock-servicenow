const test = require("node:test");
const assert = require("node:assert/strict");
const { buildIncidentQueryParams, shapePaginationInfo } = require("../static/js/incident-logic.js");

test("BEH-1: no filters and no page produces an empty query-param object", () => {
  assert.deepEqual(buildIncidentQueryParams({}, undefined, undefined), {});
});

test("BEH-1: pagination shape reflects page/page_size/total from the API response", () => {
  const info = shapePaginationInfo(1, 50, 120);
  assert.equal(info.page, 1);
  assert.equal(info.totalPages, 3);
  assert.equal(info.hasPrev, false);
  assert.equal(info.hasNext, true);
});

test("BEH-1: a single, exact-page-size total has no next page", () => {
  const info = shapePaginationInfo(1, 50, 50);
  assert.equal(info.hasNext, false);
});
