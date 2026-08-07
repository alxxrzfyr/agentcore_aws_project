"""MCP Client for AgentCore Gateway.

Connects to the workshop gateway using Cognito OAuth (client_credentials) for
authentication. The gateway exposes DynamoDB and Knowledge Base tools as MCP tools.
"""

import os
import time
import logging
import urllib.request
import urllib.parse
import json
import base64

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# Gateway configuration from environment variables
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")
GATEWAY_CLIENT_ID = os.environ.get("GATEWAY_CLIENT_ID", "")
GATEWAY_CLIENT_SECRET = os.environ.get("GATEWAY_CLIENT_SECRET", "")
GATEWAY_TOKEN_ENDPOINT = os.environ.get("GATEWAY_TOKEN_ENDPOINT", "")
GATEWAY_SCOPE = os.environ.get("GATEWAY_SCOPE", "gateway/invoke")

# Token cache
_cached_token: str | None = None
_token_expiry: float = 0


def _get_access_token() -> str:
    """Obtain a JWT access token from Cognito using client_credentials grant.

    Caches the token and refreshes 60 seconds before expiry.
    """
    global _cached_token, _token_expiry

    # Return cached token if still valid
    if _cached_token and time.time() < _token_expiry:
        return _cached_token

    if not all([GATEWAY_CLIENT_ID, GATEWAY_CLIENT_SECRET, GATEWAY_TOKEN_ENDPOINT]):
        raise RuntimeError(
            "Gateway OAuth credentials not configured. Set GATEWAY_CLIENT_ID, "
            "GATEWAY_CLIENT_SECRET, and GATEWAY_TOKEN_ENDPOINT environment variables."
        )

    # Build the token request
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": GATEWAY_SCOPE,
    }).encode("utf-8")

    # Basic auth header with client_id:client_secret
    credentials = base64.b64encode(
        f"{GATEWAY_CLIENT_ID}:{GATEWAY_CLIENT_SECRET}".encode()
    ).decode()

    req = urllib.request.Request(
        GATEWAY_TOKEN_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
    )

    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read())

    _cached_token = token_data["access_token"]
    # Cache with 60-second buffer before actual expiry
    expires_in = token_data.get("expires_in", 3600)
    _token_expiry = time.time() + expires_in - 60

    logger.info("Obtained new gateway access token (expires in %d seconds)", expires_in)
    return _cached_token


def get_streamable_http_mcp_client() -> MCPClient | None:
    """Returns an MCP Client that connects to the AgentCore Gateway.

    If GATEWAY_URL is not set, returns None (gateway not configured).
    """
    if not GATEWAY_URL:
        logger.warning("GATEWAY_URL not set; MCP gateway client disabled.")
        return None

    def _create_transport():
        """Factory that creates the StreamableHTTP transport with a fresh token."""
        token = _get_access_token()
        # The gateway MCP endpoint is at {gateway_url}/mcp
        mcp_url = GATEWAY_URL.rstrip("/") + "/mcp"
        return streamablehttp_client(
            mcp_url,
            headers={"Authorization": f"Bearer {token}"},
        )

    return MCPClient(_create_transport)
