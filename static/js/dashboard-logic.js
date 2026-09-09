(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DashboardLogic = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  const DASHBOARD_TILES = [
    { key: "new", label: "New", kind: "state", value: "new" },
    { key: "in_progress", label: "In Progress", kind: "state", value: "in_progress" },
    { key: "on_hold", label: "On Hold", kind: "state", value: "on_hold" },
    { key: "resolved", label: "Resolved", kind: "state", value: "resolved" },
    { key: "closed", label: "Closed", kind: "state", value: "closed" },
    { key: "escalated", label: "Escalated", kind: "escalated" },
    { key: "breached_sla", label: "Breached SLAs", kind: "info" },
  ];

  function buildTileUrl(tile) {
    if (tile.kind === "state") return `/incidents?state=${tile.value}&page_size=1`;
    if (tile.kind === "escalated") return "/incidents?escalated=true&page_size=1";
    return "/sla?breached=true&page_size=1";
  }

  function isTileClickable(tile) {
    return tile.kind !== "info";
  }

  function tileFilterParams(tile) {
    if (tile.kind === "state") return { state: tile.value };
    if (tile.kind === "escalated") return { escalated: "true" };
    return null;
  }

  return { DASHBOARD_TILES, buildTileUrl, isTileClickable, tileFilterParams };
});
