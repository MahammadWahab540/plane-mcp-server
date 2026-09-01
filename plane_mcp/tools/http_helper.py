"""Shared HTTP request helper for legacy Plane API endpoints.

Handles authentication (API key or OAuth) and proper base_url normalization
for direct HTTP calls to Plane v1.4.2 /api/ endpoints.
"""

import json
import os
from typing import Any

from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.dependencies import get_access_token


def get_base_url() -> str:
    """Get Plane base URL from environment or client config.

    Tries to read from:
    1. PLANE_INTERNAL_BASE_URL (preferred for server-to-server)
    2. PLANE_BASE_URL (fallback)
    3. Client config base_url if available
    4. Raises ValueError if no source available

    Returns:
        Base URL normalized to root (no /api/ suffix, no trailing slash)

    Raises:
        ValueError: If no base URL is available
    """
    # Try environment variables first (preferred)
    base_url = os.getenv("PLANE_INTERNAL_BASE_URL") or os.getenv("PLANE_BASE_URL")
    if base_url:
        return normalize_base_url(base_url)

    # Fall back to client config as last resort
    try:
        from plane_mcp.client import get_plane_client_context

        client, _ = get_plane_client_context()
        if hasattr(client, "config") and hasattr(client.config, "base_url") and client.config.base_url:
            return normalize_base_url(client.config.base_url)
    except Exception:
        pass

    raise ValueError(
        "No Plane base URL available. Set PLANE_BASE_URL or PLANE_INTERNAL_BASE_URL environment variable."
    )


def get_auth_headers() -> tuple[str, dict[str, str]]:
    """Get authorization headers for Plane API.

    Returns:
        tuple of (auth_header_value, headers_dict) where:
        - auth_header_value is either "Bearer <token>" or ""
        - headers_dict is {"x-api-key": key} or empty dict depending on auth method

    Raises:
        ValueError: If no authentication is available
    """
    # Check for OAuth token first
    stored_token: AccessToken | None = get_access_token()
    if stored_token:
        auth_method = stored_token.claims.get("auth_method", "oauth")
        token = stored_token.token

        if auth_method in ("api_key_env", "api_key_header"):
            # API key auth
            return "", {"x-api-key": token}
        else:
            # OAuth bearer token
            return f"Bearer {token}", {}

    # Fallback to environment API key
    api_key = os.getenv("PLANE_API_KEY", "")
    if api_key:
        return "", {"x-api-key": api_key}

    raise ValueError("No authentication available (API key or OAuth token)")


def normalize_base_url(base_url: str) -> str:
    """Normalize base_url to ensure no double /api/ path.

    Args:
        base_url: URL that may or may not have /api/ suffix

    Returns:
        Normalized URL without trailing slash or /api/
    """
    url = base_url.rstrip("/")
    if url.endswith("/api"):
        url = url[:-4]  # Remove /api suffix
    return url


def make_http_request(
    method: str,
    path: str,
    base_url: str = "",
    data: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | str]:
    """Make authenticated HTTP request to Plane API.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        path: API path starting with / (e.g., /api/workspaces/{slug}/projects/{id}/pages/)
        base_url: Base Plane URL (will be normalized). If empty, reads from env/config.
        data: Optional JSON payload

    Returns:
        tuple of (status_code, response_data)
        response_data is a dict if valid JSON, else raw string

    Raises:
        ValueError: If no authentication or base_url is available
    """
    import urllib.error
    import urllib.request

    if not base_url:
        base_url = get_base_url()
    else:
        base_url = normalize_base_url(base_url)

    auth_value, headers = get_auth_headers()

    url = f"{base_url}{path}"
    default_headers = {"Content-Type": "application/json"}
    default_headers.update(headers)

    if auth_value:
        default_headers["Authorization"] = auth_value

    req = urllib.request.Request(url, headers=default_headers, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            try:
                return response.status, json.loads(body) if body else {}
            except json.JSONDecodeError:
                return response.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(body) if body else {"error": body}
        except json.JSONDecodeError:
            return e.code, {"error": body}
    except Exception as e:
        return 500, {"error": str(e)}

