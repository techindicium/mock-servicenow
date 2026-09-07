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

  function formatNullableField(value, placeholder) {
    return value === null || value === undefined || value === "" ? placeholder : value;
  }

  function shapeIncidentRecordFields(incident) {
    return [
      { label: "Number", value: incident.number },
      { label: "Account", value: incident.account_id },
      { label: "Category", value: incident.category },
      { label: "Short description", value: incident.short_description },
      { label: "Description", value: incident.description },
      { label: "State", value: incident.state },
      { label: "Priority", value: String(incident.priority) },
      { label: "Opened at", value: incident.opened_at },
      { label: "Resolved at", value: formatNullableField(incident.resolved_at, "Not resolved") },
      { label: "Assigned to", value: formatNullableField(incident.assigned_to, "Unassigned") },
      { label: "Assignment group",
        value: formatNullableField(incident.assignment_group, "Unassigned") },
      { label: "Escalated", value: incident.escalated ? "Yes" : "No" },
    ];
  }

  function sortWorkNotesChronological(notes) {
    return [...(Array.isArray(notes) ? notes : [])].sort((a, b) =>
      a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0
    );
  }

  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
    formatNullableField, shapeIncidentRecordFields, sortWorkNotesChronological,
  };
});
