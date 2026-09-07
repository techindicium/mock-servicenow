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

  window.IncidentApp = { fetchJson, showError, clearError };
})();
