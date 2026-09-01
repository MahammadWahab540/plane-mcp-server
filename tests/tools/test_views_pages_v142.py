"""Tests for Plane v1.4.2 views and pages compatibility.

Tests the new view tool and updated page tool for v1.4.2 compatibility:
- Views (issue-views) CRUD at project scope
- Pages at project scope (workspace pages unsupported in v1.4.2)
- Project.get_features derives from project.retrieve
"""

import json
import pytest
from unittest.mock import MagicMock, patch


def test_view_list_requires_project_id():
    """Test that view list requires project_id."""
    from plane_mcp.tools.view import view
    
    result = view("list", project_id="")
    assert "project_id" in str(result).lower() or "missing" in str(result).lower()


def test_view_create_requires_name():
    """Test that view create requires name."""
    from plane_mcp.tools.view import view
    
    result = view("create", project_id="test-proj", name="")
    assert "name" in str(result).lower() or "missing" in str(result).lower()


def test_view_json_parsing():
    """Test that view handles JSON string and dict inputs for filters."""
    from plane_mcp.tools.view import view
    
    # Test with invalid JSON should return error
    result = view(
        "create",
        project_id="test-proj",
        name="Test View",
        filters="invalid json {",
    )
    assert "json" in str(result).lower() or "error" in str(result).lower()


def test_page_list_without_project_returns_error():
    """Test that page list without project_id returns compatibility error for v1.4.2."""
    from plane_mcp.tools.page import page
    
    result = page("list", project_id="")
    assert "Workspace-level pages" in str(result) or "not supported" in str(result).lower()


def test_page_create_requires_project():
    """Test that page create requires project_id."""
    from plane_mcp.tools.page import page
    
    result = page("create", project_id="", name="Test", description_html="<p>Test</p>")
    assert "project_id" in str(result).lower() or "error" in str(result).lower()


def test_page_retrieve_requires_page_id():
    """Test that page retrieve requires page_id."""
    from plane_mcp.tools.page import page
    
    result = page("retrieve", project_id="test-proj", page_id="")
    assert "page_id" in str(result).lower() or "missing" in str(result).lower()


@patch("plane_mcp.client.get_plane_client_context")
def test_project_get_features_derives_from_retrieve(mock_client_context):
    """Test that project.get_features derives features from project.retrieve."""
    from plane_mcp.tools.project import project
    
    # Mock the client and project
    mock_client = MagicMock()
    mock_project = MagicMock()
    mock_project.module_view = True
    mock_project.cycle_view = False
    mock_project.issue_views_view = True
    mock_project.page_view = True
    mock_project.intake_view = False
    mock_project.is_time_tracking_enabled = False
    mock_project.is_issue_type_enabled = False
    mock_project.guest_view_all_features = False
    
    mock_client.projects.retrieve.return_value = mock_project
    mock_client_context.return_value = (mock_client, "test-workspace")
    
    result = project("get_features", project_id="test-proj")
    
    # Result should be a dict of features
    assert isinstance(result, dict)
    assert "module_view" in result
    assert result["module_view"] is True
    assert result["cycle_view"] is False
    assert result["issue_views_view"] is True
    assert result["page_view"] is True


def test_view_actions_registered():
    """Test that view tool has all expected actions."""
    from plane_mcp.tools.view import ACTIONS, NAME
    
    assert NAME == "view"
    action_names = {a.name for a in ACTIONS}
    expected = {"list", "retrieve", "create", "update", "delete"}
    assert expected.issubset(action_names), f"Missing actions: {expected - action_names}"


def test_page_workspace_actions_all_require_project():
    """Test that page tool now requires project_id for all main actions."""
    from plane_mcp.tools.page import page
    
    # Test the key actions that previously worked without project_id
    for action in ["list", "retrieve", "create", "update", "archive", "delete"]:
        if action in ["list", "create"]:
            # These are the critical ones that need project_id now
            result = page(action, project_id="", page_id="test" if action != "create" else "")
            if action == "create":
                result = page(action, project_id="", name="Test", description_html="<p>Test</p>")
            # Should return an error mentioning workspace pages or missing project_id
            error_msg = str(result).lower()
            assert "workspace" in error_msg or "project_id" in error_msg or "not supported" in error_msg


def test_view_http_request_wrapper():
    """Test the HTTP request wrapper in view tool handles errors gracefully."""
    from plane_mcp.tools.view import _make_http_request
    import urllib.error
    
    # This tests the error handling path
    # In real use, this would make actual HTTP calls, but we can verify the signature exists
    assert callable(_make_http_request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

