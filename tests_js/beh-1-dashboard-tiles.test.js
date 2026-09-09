const test = require("node:test");
const assert = require("node:assert/strict");
const {
  DASHBOARD_TILES, buildTileUrl, isTileClickable, tileFilterParams,
} = require("../static/js/dashboard-logic.js");

test("BEH-1: exactly seven tiles — one per state, escalated, breached SLA", () => {
  assert.equal(DASHBOARD_TILES.length, 7);
  assert.deepEqual(
    DASHBOARD_TILES.map((t) => t.key),
    ["new", "in_progress", "on_hold", "resolved", "closed", "escalated", "breached_sla"]
  );
});

test("BEH-1: each state tile's URL filters /incidents by that state, page_size=1", () => {
  const tile = DASHBOARD_TILES.find((t) => t.key === "on_hold");
  assert.equal(buildTileUrl(tile), "/incidents?state=on_hold&page_size=1");
});

test("BEH-1: the escalated tile's URL filters /incidents by escalated=true, page_size=1", () => {
  const tile = DASHBOARD_TILES.find((t) => t.key === "escalated");
  assert.equal(buildTileUrl(tile), "/incidents?escalated=true&page_size=1");
});

test("BEH-1: the breached-SLA tile's URL filters /sla by breached=true, page_size=1", () => {
  const tile = DASHBOARD_TILES.find((t) => t.key === "breached_sla");
  assert.equal(buildTileUrl(tile), "/sla?breached=true&page_size=1");
});

test("BEH-2/BEH-3: state and escalated tiles are clickable, breached SLA is not", () => {
  for (const key of ["new", "in_progress", "on_hold", "resolved", "closed", "escalated"]) {
    assert.equal(isTileClickable(DASHBOARD_TILES.find((t) => t.key === key)), true);
  }
  assert.equal(isTileClickable(DASHBOARD_TILES.find((t) => t.key === "breached_sla")), false);
});

test("BEH-2: state tiles resolve to a state filter, the escalated tile to an escalated filter", () => {
  assert.deepEqual(tileFilterParams(DASHBOARD_TILES.find((t) => t.key === "new")), { state: "new" });
  assert.deepEqual(
    tileFilterParams(DASHBOARD_TILES.find((t) => t.key === "escalated")), { escalated: "true" }
  );
});

test("BEH-3: the breached-SLA tile has no filter, since it isn't clickable", () => {
  assert.equal(tileFilterParams(DASHBOARD_TILES.find((t) => t.key === "breached_sla")), null);
});
