"""Tests for robust base_url resolution independent of client.config.

Verifies that page.py and view.py work when client.config.base_url is missing
or None, falling back to PLANE_BASE_URL environment variable.
"""

from unittest.mock import MagicMock, patch

import pytest


def test_get_base_url_from_plane_base_url_env():
    """Test get_base_url reads PLANE_BASE_URL when available."""
    from plane_mcp.tools.http_helper import get_base_url

    with patch.dict("os.environ", {"PLANE_BASE_URL": "https://plane.example.com/api"}):
        result = get_base_url()
        assert result == "https://plane.example.com"


def test_get_base_url_prefers_internal_url():
    """Test get_base_url prefers PLANE_INTERNAL_BASE_URL over PLANE_BASE_URL."""
    from plane_mcp.tools.http_helper import get_base_url

    with patch.dict(
        "os.environ",
        {
            "PLANE_INTERNAL_BASE_URL": "https://plane-internal.local/api",
            "PLANE_BASE_URL": "https://plane.example.com",
        },
    ):
        result = get_base_url()
        assert result == "https://plane-internal.local"


def test_normalize_base_url_removes_api_suffix():
    """Test normalize_base_url consistently removes /api suffix."""
    from plane_mcp.tools.http_helper import normalize_base_url

    assert normalize_base_url("https://plane.example.com") == "https://plane.example.com"
    assert normalize_base_url("https://plane.example.com/") == "https://plane.example.com"
    assert normalize_base_url("https://plane.example.com/api") == "https://plane.example.com"
    assert normalize_base_url("https://plane.example.com/api/") == "https://plane.example.com"


def test_make_http_request_uses_env_base_url_by_default():
    """Test make_http_request can work without client.config.base_url."""
    from plane_mcp.tools.http_helper import make_http_request

    with patch.dict(
        "os.environ", {"PLANE_BASE_URL": "https://plane.example.com", "PLANE_API_KEY": "test-key"}
    ):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"results": []}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            status, response = make_http_request("GET", "/api/workspaces/test/projects/123/pages/")

            assert status == 200
            assert response == {"results": []}


def test_make_http_request_normalizes_provided_base_url():
    """Test make_http_request normalizes base_url when explicitly provided."""
    from plane_mcp.tools.http_helper import make_http_request

    with patch.dict("os.environ", {"PLANE_API_KEY": "test-key"}):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b'{}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            make_http_request("GET", "/api/test/", "https://plane.example.com/api/")

            called_url = mock_urlopen.call_args[0][0].full_url
            assert called_url == "https://plane.example.com/api/test/"
            assert "/api/api" not in called_url


def test_project_tool_has_view_actions():
    """Test that project tool includes view actions."""
    from plane_mcp.tools.project import ACTIONS

    action_names = {a.name for a in ACTIONS}
    view_actions = {"list_views", "retrieve_view", "create_view", "update_view", "delete_view"}
    assert view_actions.issubset(action_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

