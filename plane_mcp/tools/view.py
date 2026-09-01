"""Project saved views (issue-views). CRUD for filtered/grouped issue lists.

Saved views allow filtering, grouping, and display configuration of work items.
Only project-level views are supported in Plane v1.4.2.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from fastmcp import FastMCP

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import Action, build_annotations, build_description, missing, opt

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


def _make_http_request(
    method: str,
    path: str,
    data: dict[str, Any] | None = None,
    base_url: str = "",
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Make authenticated HTTP request to Plane API."""
    import urllib.error
    import urllib.request

    if not base_url:
        raise ValueError("base_url required")

    url = f"{base_url}{path}"
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)

    req = urllib.request.Request(url, headers=default_headers, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            try:
                return response.status, json.loads(body) if body else {}
            except json.JSONDecodeError:
                return response.status, {"raw": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            error_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            error_data = {"error": body}
        return e.code, error_data
    except Exception as e:
        return 500, {"error": str(e)}


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

        if not project_id:
            return missing(action, "project_id")

        # Get base_url and api_key from client config
        base_url = client.config.base_url.rstrip("/")
        api_key = client.config.api_key

        if not api_key:
            return "Error: API key required for view operations"

        headers = {"x-api-key": api_key}

        if action == "list":
            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/"
            if cursor:
                path += f"?cursor={cursor}"
            if per_page:
                sep = "&" if cursor else "?"
                path += f"{sep}per_page={per_page}"

            status, response = _make_http_request("GET", path, base_url=base_url, headers=headers)
            if status == 200:
                return response
            return f"Error listing views: {status} {response}"

        if action == "retrieve":
            if not view_id:
                return missing(action, "view_id")
            path = (
                f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            )
            status, response = _make_http_request("GET", path, base_url=base_url, headers=headers)
            if status == 200:
                return response
            return f"Error retrieving view: {status} {response}"

        if action == "create":
            if not name:
                return missing(action, "name")

            # Parse JSON fields if provided as strings
            filters_obj = None
            if filters:
                try:
                    filters_obj = json.loads(filters) if isinstance(filters, str) else filters
                except json.JSONDecodeError:
                    return "Error: filters must be valid JSON"

            display_filters_obj = None
            if display_filters:
                try:
                    display_filters_obj = (
                        json.loads(display_filters)
                        if isinstance(display_filters, str)
                        else display_filters
                    )
                except json.JSONDecodeError:
                    return "Error: display_filters must be valid JSON"

            display_properties_obj = None
            if display_properties:
                try:
                    display_properties_obj = (
                        json.loads(display_properties)
                        if isinstance(display_properties, str)
                        else display_properties
                    )
                except json.JSONDecodeError:
                    return "Error: display_properties must be valid JSON"

            rich_filters_obj = None
            if rich_filters:
                try:
                    rich_filters_obj = (
                        json.loads(rich_filters) if isinstance(rich_filters, str) else rich_filters
                    )
                except json.JSONDecodeError:
                    return "Error: rich_filters must be valid JSON"

            data = {
                "name": name,
                "description": opt(description),
                "access": access,
                "filters": filters_obj,
                "display_filters": display_filters_obj,
                "display_properties": display_properties_obj,
                "rich_filters": rich_filters_obj,
                "sort_order": opt(sort_order) if sort_order else None,
            }
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/"
            status, response = _make_http_request("POST", path, data=data, base_url=base_url, headers=headers)
            if status in (200, 201):
                return response
            return f"Error creating view: {status} {response}"

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

            # Parse JSON fields if provided as strings
            filters_obj = None
            if filters:
                try:
                    filters_obj = json.loads(filters) if isinstance(filters, str) else filters
                except json.JSONDecodeError:
                    return "Error: filters must be valid JSON"

            display_filters_obj = None
            if display_filters:
                try:
                    display_filters_obj = (
                        json.loads(display_filters)
                        if isinstance(display_filters, str)
                        else display_filters
                    )
                except json.JSONDecodeError:
                    return "Error: display_filters must be valid JSON"

            display_properties_obj = None
            if display_properties:
                try:
                    display_properties_obj = (
                        json.loads(display_properties)
                        if isinstance(display_properties, str)
                        else display_properties
                    )
                except json.JSONDecodeError:
                    return "Error: display_properties must be valid JSON"

            rich_filters_obj = None
            if rich_filters:
                try:
                    rich_filters_obj = (
                        json.loads(rich_filters) if isinstance(rich_filters, str) else rich_filters
                    )
                except json.JSONDecodeError:
                    return "Error: rich_filters must be valid JSON"

            data = {
                "name": opt(name),
                "description": opt(description),
                "access": access,
                "filters": filters_obj,
                "display_filters": display_filters_obj,
                "display_properties": display_properties_obj,
                "rich_filters": rich_filters_obj,
                "sort_order": opt(sort_order) if sort_order else None,
            }
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}

            path = (
                f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            )
            status, response = _make_http_request("PATCH", path, data=data, base_url=base_url, headers=headers)
            if status == 200:
                return response
            return f"Error updating view: {status} {response}"

        if action == "delete":
            if not view_id:
                return missing(action, "view_id")
            path = (
                f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            )
            status, response = _make_http_request("DELETE", path, base_url=base_url, headers=headers)
            if status in (200, 204):
                return None
            return f"Error deleting view: {status} {response}"

