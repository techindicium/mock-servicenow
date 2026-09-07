import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict

mcp = MCPServer("mock-servicenow-mcp")

# Strict-schema patch (see plan header design decision): the installed mcp SDK's auto-generated
# per-tool argument model does not set extra="forbid" by default (pydantic v2's own default is
# extra="ignore"), so a zero-parameter tool (e.g. user-tools.spec.md's list_users) would otherwise
# silently drop unexpected arguments and proceed to the real HTTP call instead of erroring first.
# Tightening the shared ArgModelBase every generated argument model inherits from makes every
# tool's input schema strict — an unknown key is rejected at validation time, before the tool body
# (and therefore any HTTP call) ever runs, and the published JSON schema carries
# additionalProperties: false. This must run before any tool module is imported, since each
# @mcp.tool()-decorated function builds its argument model at decoration time. Applied once, here
# — sibling tool modules (work_notes, escalations, sla, users) rely on this already being in
# place; none of them re-apply it.
ArgModelBase.model_config = ConfigDict(extra="forbid")


def main() -> None:
    # Each mcp-server tool plan (incident-tools, work-note-tools, escalation-and-sla-tools,
    # user-tools) adds its own import line here as a side-effecting registration step; the line
    # below is incident-tools' own contribution to the shared list.
    import mcp_server.tools.incidents  # noqa: F401  (import registers the tools as a side effect)
    import mcp_server.tools.escalations  # noqa: F401  (escalation-and-sla-tools' contribution)

    # See mock-jira/mcp_server/server.py for why this re-import-by-qualified-name is required:
    # running this file as `python -m mcp_server.server` loads it into sys.modules as `__main__`,
    # a separate module object from `mcp_server.server`. The tool modules' absolute imports
    # (`from mcp_server.server import mcp`) trigger a second, independent import of this file
    # under its real package name, registering every @mcp.tool() onto *that* instance instead of
    # the `__main__`-local `mcp` global above.
    from mcp_server.server import mcp as _mcp

    port = os.environ.get("PORT")
    if port:
        _mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        _mcp.run()


if __name__ == "__main__":
    main()
