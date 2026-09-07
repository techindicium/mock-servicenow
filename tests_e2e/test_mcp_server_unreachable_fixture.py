import socket


def test_mcp_server_unreachable_starts_only_mcp_server(mcp_server_unreachable):
    host, port = mcp_server_unreachable.replace("http://", "").split(":")
    with socket.create_connection((host, int(port)), timeout=2):
        pass  # mcp-server itself is up, even though its upstream is dead
