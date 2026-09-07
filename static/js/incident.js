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

  window.IncidentApp = {
    fetchJson, showError, clearError, loadIncidentList, renderIncidentList, renderIncidentRow,
  };
})();
