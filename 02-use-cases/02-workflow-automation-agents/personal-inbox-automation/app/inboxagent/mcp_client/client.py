"""MCP client for the AgentCore Gateway (AWS_IAM / SigV4 mode)."""
import logging
from typing import Optional
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient
from config import GATEWAY_URL

log = logging.getLogger(__name__)
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> Optional[MCPClient]:
    """Get or create the Gateway MCP client. Returns None if not configured."""
    global _mcp_client  # noqa: PLW0603
    if not GATEWAY_URL:
        return None
    if _mcp_client:
        return _mcp_client

    def _transport():
        return streamablehttp_client(GATEWAY_URL)

    _mcp_client = MCPClient(_transport)
    return _mcp_client
