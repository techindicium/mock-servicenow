function renderTable(selector, rows, columns) {
  const tbody = document.querySelector(`${selector} tbody`);
  tbody.textContent = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of columns) {
      const td = document.createElement("td");
      td.textContent = row[key]; // textContent only — never innerHTML
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function loadDirectoryView() {
  try {
    const [usersResp, groupsResp] = await Promise.all([fetch("/users"), fetch("/assignment_groups")]);
    if (!usersResp.ok) throw { status: usersResp.status, source: "users" };
    if (!groupsResp.ok) throw { status: groupsResp.status, source: "assignment_groups" };
    const usersBody = await usersResp.json();
    const groupsBody = await groupsResp.json();
    renderTable("#users-table", usersBody.items.map(DirectoryLogic.userRowCells), ["name", "role", "assignment_group"]);
    renderTable("#assignment-groups-table", groupsBody.items.map(DirectoryLogic.groupRowCells), ["name"]);
  } catch (err) {
    showDirectoryError(UiErrors.formatApiError(`Loading ${err.source || "directory"}`, err));
  }
}

function showDirectoryError(message) {
  const el = document.getElementById("directory-error");
  el.textContent = message;
  el.hidden = false;
}
