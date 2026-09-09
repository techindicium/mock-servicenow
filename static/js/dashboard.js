(function () {
  function navigateToFilteredIncidents(filter) {
    const recordView = document.getElementById("incident-record-view");
    if (!recordView.hidden) document.getElementById("back-to-list").click();
    const createView = document.getElementById("create-incident");
    if (!createView.hidden) document.getElementById("cancel-create-incident").click();
    document.getElementById("nav-incidents").click();

    const form = document.getElementById("incident-filter-form");
    form.state.value = (filter && filter.state) || "";
    form.escalated.value = (filter && filter.escalated) || "";
    form.category.value = "";
    form.account_id.value = "";
    form.requestSubmit();
  }

  function renderTile(tile, outcome) {
    const wrapper = document.createElement("div");
    wrapper.className = "dashboard-tile";
    wrapper.dataset.tile = tile.key;

    if (outcome.status === "rejected") {
      const errorEl = document.createElement("p");
      errorEl.className = "dashboard-tile-error";
      errorEl.textContent = UiErrors.formatApiError(`Loading ${tile.label}`, outcome.reason || {});
      wrapper.appendChild(errorEl);
    } else if (DashboardLogic.isTileClickable(tile)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "dashboard-tile-value";
      button.textContent = String(outcome.value);
      button.addEventListener("click", () => {
        navigateToFilteredIncidents(DashboardLogic.tileFilterParams(tile));
      });
      wrapper.appendChild(button);
    } else {
      const span = document.createElement("span");
      span.className = "dashboard-tile-value";
      span.textContent = String(outcome.value); // never a <button> or link — BEH-3
      wrapper.appendChild(span);
    }

    const label = document.createElement("p");
    label.className = "dashboard-tile-label";
    label.textContent = tile.label;
    wrapper.appendChild(label);
    return wrapper;
  }

  async function fetchTileTotal(tile) {
    let resp;
    try {
      resp = await fetch(DashboardLogic.buildTileUrl(tile));
    } catch (networkErr) {
      throw { message: networkErr.message };
    }
    if (!resp.ok) throw { status: resp.status };
    const body = await resp.json();
    return body.total;
  }

  async function loadDashboardView() {
    const container = document.getElementById("dashboard-tiles");
    container.innerHTML = ""; // full replace — BEH-5: a revisit never mixes stale tiles in
    const settled = await Promise.allSettled(
      DashboardLogic.DASHBOARD_TILES.map((tile) => fetchTileTotal(tile))
    );
    DashboardLogic.DASHBOARD_TILES.forEach((tile, i) => {
      const outcome = settled[i].status === "fulfilled"
        ? { status: "fulfilled", value: settled[i].value }
        : { status: "rejected", reason: settled[i].reason };
      container.appendChild(renderTile(tile, outcome));
    });
  }

  window.loadDashboardView = loadDashboardView;
})();
