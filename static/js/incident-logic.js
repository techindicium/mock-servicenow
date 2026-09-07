(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.IncidentLogic = factory();
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  const INCIDENT_STATES = ["new", "in_progress", "on_hold", "resolved", "closed"];
  const PRIORITIES = [1, 2, 3, 4];
  const NOTE_TYPES = ["comment", "work_note", "state_change", "proposal_sent"];

  function formatFetchError(action, error) {
    if (error && error.status) {
      return `${action} failed (HTTP ${error.status}): ${error.message || "unexpected error"}`;
    }
    return `${action} failed: ${(error && error.message) || "network error"}`;
  }

  return { INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError };
});
