(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.EscalationsLogic = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  const OWNER_UNASSIGNED_LABEL = "Unassigned";

  function displayOwner(owner) {
    return owner === null || owner === undefined ? OWNER_UNASSIGNED_LABEL : owner;
  }

  function escalationRowCells(escalation) {
    // incident_number is deliberately excluded — charter's escalations-screen scope.
    return {
      number: escalation.number,
      account_id: escalation.account_id,
      summary: escalation.summary,
      opened_at: escalation.opened_at,
      closed_at: escalation.closed_at,
      owner: displayOwner(escalation.owner),
      ownerIsUnassigned: escalation.owner === null || escalation.owner === undefined,
    };
  }

  function buildEscalationPatchPayload(original, edited) {
    const payload = {};
    if (edited.summary !== original.summary) payload.summary = edited.summary;
    if (edited.closed_at !== original.closed_at) payload.closed_at = edited.closed_at || null;
    const newOwner = edited.owner === "" ? null : edited.owner;
    if (newOwner !== original.owner) payload.owner = newOwner;
    return payload;
  }

  return { OWNER_UNASSIGNED_LABEL, displayOwner, escalationRowCells, buildEscalationPatchPayload };
});
