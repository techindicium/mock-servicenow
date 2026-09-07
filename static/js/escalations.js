let escalationsCache = [];

function renderEscalationsTable(escalations) {
  const tbody = document.querySelector("#escalations-table tbody");
  tbody.textContent = "";
  for (const escalation of escalations) {
    const cells = EscalationsLogic.escalationRowCells(escalation);
    const row = document.createElement("tr");
    row.dataset.number = cells.number;
    for (const key of ["number", "account_id", "summary", "opened_at", "closed_at"]) {
      const td = document.createElement("td");
      td.textContent = cells[key] || "";
      row.appendChild(td);
    }
    const ownerTd = document.createElement("td");
    ownerTd.textContent = cells.owner; // textContent only — never innerHTML
    if (cells.ownerIsUnassigned) ownerTd.classList.add("owner-unassigned");
    row.appendChild(ownerTd);
    row.addEventListener("click", () => openEscalationEditForm(escalation));
    tbody.appendChild(row);
  }
}

function openEscalationEditForm(escalation) {
  const form = document.getElementById("escalation-edit-form");
  form.hidden = false;
  form.elements.number.value = escalation.number;
  form.elements.summary.value = escalation.summary;
  form.elements.owner.value = escalation.owner || "";
  form.elements.closed_at.value = escalation.closed_at || "";
}

async function loadEscalationsView() {
  try {
    const resp = await fetch("/escalations");
    if (!resp.ok) throw { status: resp.status };
    const body = await resp.json();
    escalationsCache = body.items;
    renderEscalationsTable(escalationsCache);
  } catch (err) {
    showEscalationsError(UiErrors.formatApiError("Loading escalations", err));
  }
}

document.getElementById("escalation-edit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const number = form.elements.number.value;
  const original = escalationsCache.find((e) => e.number === number);
  const edited = {
    summary: form.elements.summary.value,
    owner: form.elements.owner.value,
    closed_at: form.elements.closed_at.value,
  };
  const payload = EscalationsLogic.buildEscalationPatchPayload(original, edited);
  try {
    const resp = await fetch(`/escalations/${encodeURIComponent(number)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw { status: resp.status };
    await loadEscalationsView();
    form.hidden = true;
  } catch (err) {
    showEscalationsError(
      err.status === 404
        ? UiErrors.escalationNotFoundMessage(number)
        : UiErrors.formatApiError("Saving escalation", err)
    );
  }
});

function showEscalationsError(message) {
  const el = document.getElementById("escalations-error");
  el.textContent = message;
  el.hidden = false;
}
