"""Tests for Plane v1.4.2 hardening: auth, HTTP helpers, legacy endpoints.

Covers:
- API key authentication
- OAuth bearer token authentication
- Base URL normalization
- Project page legacy HTTP routes
- Project saved view legacy HTTP routes
"""

from unittest.mock import MagicMock, patch

import pytest


def test_http_helper_normalize_base_url():
    """Test base_url normalization removes /api suffix and trailing slashes."""
    from plane_mcp.tools.http_helper import normalize_base_url

    # Normal HTTPS URL
    assert normalize_base_url("https://plane.example.com") == "https://plane.example.com"

    # With trailing slash
    assert normalize_base_url("https://plane.example.com/") == "https://plane.example.com"

    # With /api suffix
    assert normalize_base_url("https://plane.example.com/api") == "https://plane.example.com"

    # With /api and trailing slash
    assert normalize_base_url("https://plane.example.com/api/") == "https://plane.example.com"


def test_http_helper_get_auth_headers_api_key():
    """Test get_auth_headers returns x-api-key header for API key auth."""
    from plane_mcp.tools.http_helper import get_auth_headers

    test_key = "test-api-key-12345"

    with patch("plane_mcp.tools.http_helper.get_access_token") as mock_get_token:
        with patch.dict("os.environ", {"PLANE_API_KEY": test_key}):
            # Mock OAuth token as not available
            mock_get_token.return_value = None

            auth_value, headers = get_auth_headers()

            assert auth_value == ""
            assert headers == {"x-api-key": test_key}


def test_http_helper_get_auth_headers_oauth():
    """Test get_auth_headers returns Bearer token for OAuth auth."""
    from plane_mcp.tools.http_helper import get_auth_headers

    test_token = "oauth-token-xyz789"

    with patch("plane_mcp.tools.http_helper.get_access_token") as mock_get_token:
        mock_token = MagicMock()
        mock_token.token = test_token
        mock_token.claims = {"auth_method": "oauth"}
        mock_get_token.return_value = mock_token

        auth_value, headers = get_auth_headers()

        assert auth_value == f"Bearer {test_token}"
        assert headers == {}


def test_http_helper_get_auth_headers_oauth_from_claims():
    """Test get_auth_headers handles OAuth token from claims."""
    from plane_mcp.tools.http_helper import get_auth_headers

    test_token = "oauth-token-from-claims"

    with patch("plane_mcp.tools.http_helper.get_access_token") as mock_get_token:
        mock_token = MagicMock()
        mock_token.token = test_token
        mock_token.claims = {"auth_method": "oauth", "workspace_slug": "test"}
        mock_get_token.return_value = mock_token

        auth_value, headers = get_auth_headers()

        assert auth_value == f"Bearer {test_token}"
        assert headers == {}


def test_http_helper_get_auth_headers_no_auth():
    """Test get_auth_headers raises ValueError when no auth is available."""
    from plane_mcp.tools.http_helper import get_auth_headers

    with patch("plane_mcp.tools.http_helper.get_access_token") as mock_get_token:
        with patch.dict("os.environ", {}, clear=True):
            mock_get_token.return_value = None

            with pytest.raises(ValueError, match="No authentication"):
                get_auth_headers()


def test_http_helper_make_request_normalizes_base_url():
    """Test make_http_request normalizes base_url."""
    from plane_mcp.tools.http_helper import make_http_request

    with patch("plane_mcp.tools.http_helper.get_auth_headers") as mock_auth:
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_auth.return_value = ("", {"x-api-key": "test"})
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"success": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            status, response = make_http_request(
                "GET",
                "/api/workspaces/test/projects/123/pages/",
                "https://plane.example.com/api/",
            )

            # Verify URL was normalized (no double /api)
            called_url = mock_urlopen.call_args[0][0].full_url
            assert (
                called_url
                == "https://plane.example.com/api/workspaces/test/projects/123/pages/"
            )
            assert status == 200


def test_page_tool_routes_registered():
    """Test that page tool is registered with correct routes."""
    from plane_mcp.tools.page import ACTIONS, NAME

    assert NAME == "page"
    action_names = {a.name for a in ACTIONS}
    expected = {
        "list",
        "retrieve",
        "create",
        "update",
        "archive",
        "delete",
        "list_workitem_pages",
        "attach_to_workitem",
        "detach_from_workitem",
    }
    assert expected.issubset(action_names)


def test_view_tool_routes_registered():
    """Test that view tool is registered with correct routes."""
    from plane_mcp.tools.view import ACTIONS, NAME

    assert NAME == "view"
    action_names = {a.name for a in ACTIONS}
    expected = {"list", "retrieve", "create", "update", "delete"}
    assert expected.issubset(action_names)


def test_view_parse_json_field_handles_strings():
    """Test view tool's JSON field parsing with string inputs."""
    from plane_mcp.tools.view import _parse_json_field

    # Valid JSON string
    result = _parse_json_field('{"key": "value"}')
    assert result == {"key": "value"}

    # Dict input
    result = _parse_json_field({"key": "value"})
    assert result == {"key": "value"}

    # Empty/None
    result = _parse_json_field(None)
    assert result is None

    result = _parse_json_field("")
    assert result is None


def test_view_parse_json_field_rejects_invalid():
    """Test view tool's JSON field parsing rejects invalid JSON."""
    from plane_mcp.tools.view import _parse_json_field

    # Invalid JSON returns None
    result = _parse_json_field("invalid json {")
    assert result is None


def test_http_helper_auth_from_api_key_env():
    """Test that API key from environment is used in auth headers."""
    from plane_mcp.tools.http_helper import get_auth_headers

    with patch("plane_mcp.tools.http_helper.get_access_token") as mock_token:
        with patch.dict("os.environ", {"PLANE_API_KEY": "env-api-key"}):
            mock_token.return_value = None

            auth_value, headers = get_auth_headers()

            assert headers["x-api-key"] == "env-api-key"


def test_http_helper_oauth_prefers_oauth_token():
    """Test that OAuth token takes priority over environment API key."""
    from plane_mcp.tools.http_helper import get_auth_headers

    oauth_token = "oauth-priority"

    with patch("plane_mcp.tools.http_helper.get_access_token") as mock_token:
        with patch.dict("os.environ", {"PLANE_API_KEY": "env-api-key"}):
            mock_stored = MagicMock()
            mock_stored.token = oauth_token
            mock_stored.claims = {"auth_method": "oauth"}
            mock_token.return_value = mock_stored

            auth_value, headers = get_auth_headers()

            # OAuth should take priority
            assert auth_value == f"Bearer {oauth_token}"
            assert "x-api-key" not in headers


def test_page_legacy_routes_documented():
    """Test that page tool documents legacy routes in FOOTER."""
    from plane_mcp.tools.page import FOOTER

    assert "v1.4.2" in FOOTER.lower() or "project pages" in FOOTER.lower()


def test_view_legacy_routes_documented():
    """Test that view tool documents legacy routes in FOOTER."""
    from plane_mcp.tools.view import FOOTER

    assert "v1.4.2" in FOOTER.lower() or "issue-views" in FOOTER.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

