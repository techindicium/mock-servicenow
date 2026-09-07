(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.UiErrors = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  function formatApiError(action, error) {
    if (error && error.status) {
      return `${action} failed (HTTP ${error.status})`;
    }
    return `${action} failed: network error`;
  }

  function escalationNotFoundMessage(number) {
    return `Escalation ${number} not found`;
  }

  return { formatApiError, escalationNotFoundMessage };
});
