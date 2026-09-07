(function () {
  const loadedViews = new Set(["incidents"]); // Incidents is server-rendered on page load

  function showView(activeView) {
    const visibility = NavLogic.viewVisibility(activeView);
    for (const view of NavLogic.NAV_VIEWS) {
      const section = document.getElementById(`view-${view}`);
      if (section) section.hidden = !visibility[view];
      const navBtn = document.getElementById(`nav-${view}`);
      if (navBtn) {
        navBtn.classList.toggle("active", visibility[view]);
        if (visibility[view]) navBtn.setAttribute("aria-current", "page");
        else navBtn.removeAttribute("aria-current");
      }
    }
  }

  let currentView = NavLogic.DEFAULT_VIEW;

  function onNavClick(event) {
    const requestedView = event.currentTarget.dataset.view;
    currentView = NavLogic.resolveActiveView(requestedView, currentView);
    showView(currentView);
    if (currentView === "escalations" && !loadedViews.has("escalations")) {
      loadedViews.add("escalations");
      if (typeof loadEscalationsView === "function") loadEscalationsView();
    }
    if (currentView === "directory" && !loadedViews.has("directory")) {
      loadedViews.add("directory");
      if (typeof loadDirectoryView === "function") loadDirectoryView();
    }
  }

  const navButtonIds = {
    incidents: document.getElementById("nav-incidents"),
    escalations: document.getElementById("nav-escalations"),
    directory: document.getElementById("nav-directory"),
  };
  for (const view of NavLogic.NAV_VIEWS) {
    const navBtn = navButtonIds[view];
    if (navBtn) navBtn.addEventListener("click", onNavClick);
  }

  showView(currentView);
})();
