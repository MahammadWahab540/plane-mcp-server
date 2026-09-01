"""Project saved views (issue-views). CRUD for filtered/grouped issue lists.

Saved views allow filtering, grouping, and display configuration of work items.
Only project-level views are supported in Plane v1.4.2 via:
- GET/POST /api/workspaces/{slug}/projects/{project_id}/issue-views/
- GET/PATCH/DELETE /api/workspaces/{slug}/projects/{project_id}/issue-views/{view_id}/
"""

from __future__ import annotations

import json
from typing import Any, Literal

from fastmcp import FastMCP

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import Action, build_annotations, build_description, missing
from plane_mcp.tools.http_helper import make_http_request

NAME = "view"
TITLE = "Saved Views (Issue Views)"

ACTIONS = (
    Action("list", ("project_id",), ("cursor", "per_page"), note="list saved views in a project", read=True),
    Action("retrieve", ("project_id", "view_id"), read=True),
    Action(
        "create",
        ("project_id", "name"),
        (
            "description",
            "access",
            "filters",
            "display_filters",
            "display_properties",
            "rich_filters",
            "sort_order",
        ),
        note="filters/display_filters/display_properties are JSON; pass as strings",
    ),
    Action(
        "update",
        ("project_id", "view_id"),
        (
            "name",
            "description",
            "access",
            "filters",
            "display_filters",
            "display_properties",
            "rich_filters",
            "sort_order",
        ),
        note="update only the fields you pass",
    ),
    Action("delete", ("project_id", "view_id"), destructive=True),
)

FOOTER = (
    "Saved views (issue-views in Plane v1.4.2) configure filtering, grouping, and display of work items. "
    "Fields: name, description, access (0=private, 1=public), filters, display_filters, "
    "display_properties, rich_filters (JSON objects), sort_order (float). "
    "query, owned_by, is_locked, workspace, project are read-only."
)

LEGACY = {}


def _parse_json_field(value: str | dict | None) -> dict[str, Any] | None:
    """Parse JSON field, handling both string and dict inputs."""
    if not value:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name=NAME,
        description=build_description(
            "Project saved views (issue-views) for filtering and grouping work items.", ACTIONS, FOOTER
        ),
        annotations=build_annotations(TITLE, ACTIONS),
    )
    def view(
        action: Literal["list", "retrieve", "create", "update", "delete"],
        project_id: str = "",
        view_id: str = "",
        name: str = "",
        description: str = "",
        access: int | None = None,
        filters: str = "",
        display_filters: str = "",
        display_properties: str = "",
        rich_filters: str = "",
        sort_order: float = 0.0,
        cursor: str = "",
        per_page: int = 0,
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        client, workspace_slug = get_plane_client_context()
        base_url = client.config.base_url

        if not project_id:
            return missing(action, "project_id")

        # List saved views
        if action == "list":
            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/"
            if cursor or per_page:
                query_parts = []
                if cursor:
                    query_parts.append(f"cursor={cursor}")
                if per_page:
                    query_parts.append(f"per_page={per_page}")
                path += f"?{'&'.join(query_parts)}"

            status, response = make_http_request("GET", path, base_url)
            if status == 200:
                return response
            return f"Error listing views: {status} {response}"

        # Retrieve a saved view
        if action == "retrieve":
            if not view_id:
                return missing(action, "view_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            status, response = make_http_request("GET", path, base_url)
            if status == 200:
                return response
            return f"Error retrieving view: {status} {response}"

        # Create a saved view
        if action == "create":
            if not name:
                return missing(action, "name")

            data = {"name": name}
            if description:
                data["description"] = description
            if access is not None:
                data["access"] = access

            # Parse JSON fields
            filters_obj = _parse_json_field(filters)
            if filters_obj is not None:
                data["filters"] = filters_obj
            elif filters:
                return "Error: filters must be valid JSON"

            display_filters_obj = _parse_json_field(display_filters)
            if display_filters_obj is not None:
                data["display_filters"] = display_filters_obj
            elif display_filters:
                return "Error: display_filters must be valid JSON"

            display_properties_obj = _parse_json_field(display_properties)
            if display_properties_obj is not None:
                data["display_properties"] = display_properties_obj
            elif display_properties:
                return "Error: display_properties must be valid JSON"

            rich_filters_obj = _parse_json_field(rich_filters)
            if rich_filters_obj is not None:
                data["rich_filters"] = rich_filters_obj
            elif rich_filters:
                return "Error: rich_filters must be valid JSON"

            if sort_order:
                data["sort_order"] = sort_order

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/"
            status, response = make_http_request("POST", path, base_url, data=data)
            if status in (200, 201):
                return response
            return f"Error creating view: {status} {response}"

        # Update a saved view
        if action == "update":
            if not view_id:
                return missing(action, "view_id")

            has_update = (
                name
                or description
                or access is not None
                or filters
                or display_filters
                or display_properties
                or rich_filters
                or sort_order
            )
            if not has_update:
                return "Error: provide at least one field to update"

            data = {}
            if name:
                data["name"] = name
            if description:
                data["description"] = description
            if access is not None:
                data["access"] = access

            # Parse JSON fields
            filters_obj = _parse_json_field(filters)
            if filters_obj is not None:
                data["filters"] = filters_obj
            elif filters:
                return "Error: filters must be valid JSON"

            display_filters_obj = _parse_json_field(display_filters)
            if display_filters_obj is not None:
                data["display_filters"] = display_filters_obj
            elif display_filters:
                return "Error: display_filters must be valid JSON"

            display_properties_obj = _parse_json_field(display_properties)
            if display_properties_obj is not None:
                data["display_properties"] = display_properties_obj
            elif display_properties:
                return "Error: display_properties must be valid JSON"

            rich_filters_obj = _parse_json_field(rich_filters)
            if rich_filters_obj is not None:
                data["rich_filters"] = rich_filters_obj
            elif rich_filters:
                return "Error: rich_filters must be valid JSON"

            if sort_order:
                data["sort_order"] = sort_order

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            status, response = make_http_request("PATCH", path, base_url, data=data)
            if status == 200:
                return response
            return f"Error updating view: {status} {response}"

        # Delete a saved view
        if action == "delete":
            if not view_id:
                return missing(action, "view_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            status, response = make_http_request("DELETE", path, base_url)
            if status in (200, 204):
                return None
            return f"Error deleting view: {status} {response}"

