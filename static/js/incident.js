(function () {
  async function fetchJson(url, options) {
    let resp;
    try {
      resp = await fetch(url, options);
    } catch (networkErr) {
      throw { message: networkErr.message };
    }
    if (!resp.ok) {
      let body = null;
      try {
        body = await resp.json();
      } catch (_parseErr) {
        // non-JSON error body — body stays null, message falls back below
      }
      throw { status: resp.status, message: body && body.message };
    }
    return resp.status === 204 ? null : resp.json();
  }

  function showError(message) {
    const banner = document.getElementById("incidents-error");
    banner.textContent = message;
    banner.hidden = false;
  }

  function clearError() {
    document.getElementById("incidents-error").hidden = true;
  }

  const PAGE_SIZE = 50;
  let currentFilters = {};
  let currentPage = 1;

  function renderIncidentRow(incident) {
    const tr = document.createElement("tr");
    tr.dataset.number = incident.number;
    tr.dataset.priority = String(incident.priority);
    tr.dataset.state = incident.state;
    if (incident.escalated) tr.dataset.escalated = "true";
    const cells = [
      incident.number, incident.short_description, incident.state,
      String(incident.priority), incident.category, incident.account_id,
      incident.escalated ? "Yes" : "No",
    ];
    for (const value of cells) {
      const td = document.createElement("td");
      td.textContent = value; // safe DOM insertion — never innerHTML (Postconditions)
      tr.appendChild(td);
    }
    return tr;
  }

  function renderIncidentList(page) {
    const body = document.getElementById("incidents-table-body");
    body.innerHTML = ""; // full replace — BEH-2/Postconditions: never mixes old+new results
    for (const incident of page.items) body.appendChild(renderIncidentRow(incident));
    const info = IncidentLogic.shapePaginationInfo(page.page, page.page_size, page.total);
    document.getElementById("incidents-page-info").textContent =
      `Page ${info.page} of ${info.totalPages} (${info.total} total)`;
    document.getElementById("incidents-prev-page").disabled = !info.hasPrev;
    document.getElementById("incidents-next-page").disabled = !info.hasNext;
  }

  async function loadIncidentList() {
    const params = IncidentLogic.buildIncidentQueryParams(currentFilters, currentPage, PAGE_SIZE);
    const query = new URLSearchParams(params).toString();
    try {
      const page = await fetchJson(`/incidents${query ? "?" + query : ""}`);
      clearError();
      renderIncidentList(page);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading incidents", err));
    }
  }

  function onFilterSubmit(event) {
    event.preventDefault();
    const form = event.target;
    currentFilters = {
      state: form.state.value, category: form.category.value,
      account_id: form.account_id.value, escalated: form.escalated.value,
    };
    currentPage = 1;
    loadIncidentList(); // fully replaces the table body — never merges with the prior filter set
  }

  function onPrevPage() {
    if (currentPage > 1) { currentPage -= 1; loadIncidentList(); }
  }

  function onNextPage() {
    currentPage += 1;
    loadIncidentList();
  }

  document.getElementById("incident-filter-form").addEventListener("submit", onFilterSubmit);
  document.getElementById("incidents-prev-page").addEventListener("click", onPrevPage);
  document.getElementById("incidents-next-page").addEventListener("click", onNextPage);
  document.addEventListener("DOMContentLoaded", loadIncidentList);

  function populateStateOptions(selectEl, includeBlank) {
    if (includeBlank) selectEl.appendChild(new Option("All", ""));
    for (const state of IncidentLogic.INCIDENT_STATES) selectEl.appendChild(new Option(state, state));
  }
  populateStateOptions(document.getElementById("filter-state"), true);

  let currentIncident = null;

  function populateSelectOptions(selectEl, values) {
    selectEl.innerHTML = "";
    for (const value of values) selectEl.appendChild(new Option(String(value), String(value)));
  }
  populateSelectOptions(document.getElementById("edit-state"), IncidentLogic.INCIDENT_STATES);
  populateSelectOptions(document.getElementById("edit-priority"), IncidentLogic.PRIORITIES);

  function populateEditForm(incident) {
    document.getElementById("edit-state").value = incident.state;
    document.getElementById("edit-priority").value = String(incident.priority);
    document.getElementById("edit-assigned_to").value = incident.assigned_to || "";
    document.getElementById("edit-assignment_group").value = incident.assignment_group || "";
  }

  function renderRecordFields(incident) {
    const dl = document.getElementById("record-fields");
    dl.innerHTML = ""; // full replace — Postconditions: no stale field survives a new load
    for (const { label, value } of IncidentLogic.shapeIncidentRecordFields(incident)) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value; // safe DOM insertion for user-supplied text fields too
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    document.getElementById("record-number").textContent = incident.number;
    populateEditForm(incident);
  }

  function renderWorkNoteRow(note) {
    const li = document.createElement("li");
    li.dataset.noteType = note.note_type;
    const meta = document.createElement("p");
    meta.className = "work-note-meta";
    meta.textContent = `${note.created_by} · ${note.note_type} · ${note.created_at}`;
    const body = document.createElement("p");
    body.textContent = note.body; // safe DOM insertion — created_by/body are unguarded free text
    li.appendChild(meta);
    li.appendChild(body);
    return li;
  }

  function renderWorkNoteTimeline(notes) {
    const ol = document.getElementById("work-notes-timeline");
    ol.innerHTML = "";
    for (const note of IncidentLogic.sortWorkNotesChronological(notes)) {
      ol.appendChild(renderWorkNoteRow(note));
    }
  }

  function renderSlaRow(row) {
    const tr = document.createElement("tr");
    if (row.breachClass) tr.className = row.breachClass;
    const cells = [
      row.sla_definition, String(row.target_minutes),
      row.actual_minutes === null ? "—" : String(row.actual_minutes),
      row.has_breached ? "Yes" : "No", row.business_time_only ? "Yes" : "No",
    ];
    for (const value of cells) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }
    return tr;
  }

  function renderSlaPanel(rows) {
    const body = document.getElementById("sla-table-body");
    body.innerHTML = "";
    for (const row of IncidentLogic.shapeSlaRows(rows)) body.appendChild(renderSlaRow(row));
  }

  async function loadIncidentRecord(number) {
    try {
      const incident = await fetchJson(`/incidents/${number}`);
      currentIncident = incident;
      clearError();
      renderRecordFields(incident);
      document.getElementById("incident-list-view").hidden = true;
      document.getElementById("create-incident").hidden = true;
      document.getElementById("incident-record-view").hidden = false;
    } catch (err) {
      showError(IncidentLogic.formatFetchError(`Loading incident ${number}`, err));
      return;
    }
    try {
      const notePage = await fetchJson(`/incidents/${number}/work_notes`);
      renderWorkNoteTimeline(notePage.items);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading work notes", err));
    }
    try {
      const slaPage = await fetchJson(`/sla?incident_number=${encodeURIComponent(number)}`);
      renderSlaPanel(slaPage.items);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading SLA records", err));
    }
  }

  function onIncidentRowClick(event) {
    const row = event.target.closest("tr[data-number]");
    if (row) loadIncidentRecord(row.dataset.number);
  }

  function onBackToList() {
    document.getElementById("incident-record-view").hidden = true;
    document.getElementById("incident-list-view").hidden = false;
    currentIncident = null;
  }

  document.getElementById("incidents-table-body").addEventListener("click", onIncidentRowClick);
  document.getElementById("back-to-list").addEventListener("click", onBackToList);

  function populateNoteTypeOptions() {
    const select = document.getElementById("note-note_type");
    for (const type of IncidentLogic.NOTE_TYPES) select.appendChild(new Option(type, type));
  }
  populateNoteTypeOptions();

  function showFormError(elementId, message) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.hidden = false;
  }

  function clearFormError(elementId) {
    document.getElementById(elementId).hidden = true;
  }

  async function onAddWorkNoteSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const fields = {
      created_by: form.created_by.value, note_type: form.note_type.value, body: form.body.value,
    };
    const { valid, errors } = IncidentLogic.validateWorkNoteForm(fields);
    if (!valid) {
      showFormError("add-work-note-error", Object.values(errors)[0]);
      return; // client-side block: fields the API also requires, no request sent
    }
    clearFormError("add-work-note-error");
    try {
      const created = await fetchJson(`/incidents/${currentIncident.number}/work_notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fields),
      });
      document.getElementById("work-notes-timeline").appendChild(renderWorkNoteRow(created));
      form.reset();
    } catch (err) {
      showFormError("add-work-note-error", IncidentLogic.formatFetchError("Adding work note", err));
    }
  }

  document.getElementById("add-work-note-form").addEventListener("submit", onAddWorkNoteSubmit);

  async function onEditIncidentSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const edited = {
      state: form.state.value, priority: form.priority.value,
      assigned_to: form.assigned_to.value, assignment_group: form.assignment_group.value,
    };
    const patch = IncidentLogic.diffIncidentFields(currentIncident, edited);
    if (Object.keys(patch).length === 0) {
      clearFormError("edit-incident-error");
      return; // nothing changed — no network call, no third "nothing happened" state
    }
    // No confirmation dialog, no state-transition check — BEH-7 / constitution Principle 5.
    // The save either succeeds (200) or fails with the API's own 422; there is no other outcome.
    try {
      const updated = await fetchJson(`/incidents/${currentIncident.number}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      currentIncident = updated;
      clearFormError("edit-incident-error");
      renderRecordFields(updated); // reflects the server's own post-save state (Postconditions)
    } catch (err) {
      showFormError("edit-incident-error", IncidentLogic.formatFetchError("Saving incident", err));
    }
  }

  document.getElementById("edit-incident-form").addEventListener("submit", onEditIncidentSubmit);

  populateSelectOptions(document.getElementById("create-state"), IncidentLogic.INCIDENT_STATES);
  populateSelectOptions(document.getElementById("create-priority"), IncidentLogic.PRIORITIES);

  document.getElementById("open-create-incident").addEventListener("click", () => {
    document.getElementById("incident-list-view").hidden = true;
    document.getElementById("create-incident").hidden = false;
  });
  document.getElementById("cancel-create-incident").addEventListener("click", (event) => {
    event.preventDefault();
    document.getElementById("create-incident-form").reset();
    clearFormError("create-incident-error");
    document.getElementById("create-incident").hidden = true;
    document.getElementById("incident-list-view").hidden = false;
  });

  async function onCreateIncidentSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const fields = {
      account_id: form.account_id.value, category: form.category.value,
      short_description: form.short_description.value, description: form.description.value,
      state: form.state.value, priority: form.priority.value,
    };
    const { valid, errors } = IncidentLogic.validateCreateIncidentForm(fields);
    if (!valid) {
      showFormError("create-incident-error", Object.values(errors)[0]);
      return;
    }
    clearFormError("create-incident-error");
    try {
      const created = await fetchJson("/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...fields, priority: Number(fields.priority) }),
      });
      form.reset();
      document.getElementById("create-incident").hidden = true;
      await loadIncidentRecord(created.number); // BEH-8: navigate to the new record on success
    } catch (err) {
      showFormError("create-incident-error", IncidentLogic.formatFetchError("Creating incident", err));
    }
  }

  document.getElementById("create-incident-form").addEventListener("submit", onCreateIncidentSubmit);

  window.IncidentApp = {
    fetchJson, showError, clearError, loadIncidentList, renderIncidentList, renderIncidentRow,
    loadIncidentRecord, renderRecordFields, renderWorkNoteTimeline,
  };
})();
