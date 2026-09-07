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

  function buildIncidentQueryParams(filters, page, pageSize) {
    const params = {};
    if (filters && filters.state) params.state = filters.state;
    if (filters && filters.category) params.category = filters.category;
    if (filters && filters.account_id) params.account_id = filters.account_id;
    if (filters && filters.escalated) params.escalated = filters.escalated;
    if (page) params.page = String(page);
    if (pageSize) params.page_size = String(pageSize);
    return params;
  }

  function shapePaginationInfo(page, pageSize, total) {
    const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(total / pageSize)) : 1;
    return { page, pageSize, total, totalPages, hasPrev: page > 1, hasNext: page < totalPages };
  }

  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
  };
});
