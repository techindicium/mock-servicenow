(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.NavLogic = factory();
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  const NAV_VIEWS = ["incidents", "escalations", "directory", "dashboard"];
  const DEFAULT_VIEW = "incidents";

  function isKnownView(view) {
    return NAV_VIEWS.includes(view);
  }

  function resolveActiveView(requestedView, currentView) {
    // Unknown targets are a defensive no-op — stay on the current (or
    // default) view rather than switching to an invalid state.
    if (!isKnownView(requestedView)) return isKnownView(currentView) ? currentView : DEFAULT_VIEW;
    return requestedView;
  }

  function viewVisibility(activeView) {
    const resolved = isKnownView(activeView) ? activeView : DEFAULT_VIEW;
    const visibility = {};
    for (const view of NAV_VIEWS) visibility[view] = view === resolved;
    return visibility;
  }

  return { NAV_VIEWS, DEFAULT_VIEW, isKnownView, resolveActiveView, viewVisibility };
});
