"""Project pages. Direct HTTP support for Plane v1.4.2 /api/ endpoints.

Plane v1.4.2 does not support workspace-level pages. Only project pages via:
- GET/POST /api/workspaces/{slug}/projects/{project_id}/pages/
- GET/PATCH/DELETE /api/workspaces/{slug}/projects/{project_id}/pages/{page_id}/
- POST/DELETE /api/workspaces/{slug}/projects/{project_id}/pages/{page_id}/archive/

Work-item page attachment uses SDK methods if available.
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP
from plane.models.work_item_pages import CreateWorkItemPage

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import Action, build_annotations, build_description, missing
from plane_mcp.tools.http_helper import make_http_request

NAME = "page"
TITLE = "Pages"

ACTIONS = (
    Action(
        "list",
        (),
        ("project_id", "cursor", "per_page"),
        note="project pages only in Plane v1.4.2; requires project_id",
        read=True,
    ),
    Action("retrieve", ("page_id",), ("project_id",), note="project pages only", read=True),
    Action(
        "create",
        ("project_id", "name"),
        (
            "description_html",
            "access",
            "color",
        ),
        note="project pages only in v1.4.2",
    ),
    Action(
        "update",
        ("page_id",),
        ("project_id", "name", "description_html"),
        note="project pages only; pass name, description_html, or both",
    ),
    Action(
        "archive",
        ("page_id",),
        ("project_id",),
        note="project pages only; archive/unarchive state toggle",
    ),
    Action(
        "delete",
        ("page_id",),
        ("project_id",),
        note="project pages only; requires page to be archived first",
        destructive=True,
    ),
    Action("list_workitem_pages", ("project_id", "workitem_id"), read=True),
    Action("attach_to_workitem", ("project_id", "workitem_id", "page_id")),
    Action(
        "detach_from_workitem",
        ("project_id", "workitem_id", "workitem_page_id"),
        note="workitem_page_id is the link id from list_workitem_pages, not the page id",
        destructive=True,
    ),
)

FOOTER = (
    "description_html is the page body as HTML. access is the page access level. "
    "update changes only the fields you pass. A page must be archived before deletion. "
    "Plane v1.4.2 supports project pages only. "
)

LEGACY = {
    "list_pages": "list",
    "retrieve_page": "retrieve",
    "create_page": "create",
    "list_work_item_pages": "list_workitem_pages",
    "attach_page_to_work_item": "attach_to_workitem",
    "detach_page_from_work_item": "detach_from_workitem",
}


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name=NAME,
        description=build_description(
            "Project pages (workspace pages not supported in Plane v1.4.2).", ACTIONS, FOOTER
        ),
        annotations=build_annotations(TITLE, ACTIONS),
    )
    def page(
        action: Literal[
            "list",
            "retrieve",
            "create",
            "update",
            "archive",
            "delete",
            "list_workitem_pages",
            "attach_to_workitem",
            "detach_from_workitem",
        ],
        project_id: str = "",
        page_id: str = "",
        name: str = "",
        description_html: str = "",
        access: int | None = None,
        color: str = "",
        workitem_id: str = "",
        workitem_page_id: str = "",
        cursor: str = "",
        per_page: int = 0,
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        client, workspace_slug = get_plane_client_context()
        base_url = client.config.base_url

        # List project pages
        if action == "list":
            if not project_id:
                return missing(action, "project_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/pages/"
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
            return f"Error listing pages: {status} {response}"

        # Retrieve a project page
        if action == "retrieve":
            if not project_id or not page_id:
                return missing(action, "project_id and page_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/"
            status, response = make_http_request("GET", path, base_url)
            if status == 200:
                return response
            return f"Error retrieving page: {status} {response}"

        # Create a project page
        if action == "create":
            if not project_id or not name:
                return missing(action, "project_id and name")

            data = {"name": name}
            if description_html:
                data["description_html"] = description_html
            if access is not None:
                data["access"] = access
            if color:
                data["color"] = color

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/pages/"
            status, response = make_http_request("POST", path, base_url, data=data)
            if status in (200, 201):
                return response
            return f"Error creating page: {status} {response}"

        # Update a project page
        if action == "update":
            if not project_id or not page_id:
                return missing(action, "project_id and page_id")
            if not (name or description_html):
                return missing(action, "name or description_html")

            data = {}
            if name:
                data["name"] = name
            if description_html:
                data["description_html"] = description_html

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/"
            status, response = make_http_request("PATCH", path, base_url, data=data)
            if status == 200:
                return response
            return f"Error updating page: {status} {response}"

        # Archive/unarchive a project page
        if action == "archive":
            if not project_id or not page_id:
                return missing(action, "project_id and page_id")

            # POST to /pages/{page_id}/archive/ to toggle archive state
            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/archive/"
            status, response = make_http_request("POST", path, base_url, data={})
            if status in (200, 204):
                return {"page_id": page_id, "archived": True}
            return f"Error archiving page: {status} {response}"

        # Delete a project page (requires archive first)
        if action == "delete":
            if not project_id or not page_id:
                return missing(action, "project_id and page_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/"
            status, response = make_http_request("DELETE", path, base_url)
            if status in (200, 204):
                return None
            return f"Error deleting page: {status} {response}"

        # Work-item page operations (use SDK if available)
        if action == "list_workitem_pages":
            if not project_id or not workitem_id:
                return missing(action, "project_id and workitem_id")
            try:
                response = client.work_items.pages.list(
                    workspace_slug=workspace_slug, project_id=project_id, work_item_id=workitem_id
                )
                return response.results if hasattr(response, "results") else response
            except Exception as e:
                return f"Error listing work item pages: {str(e)}"

        if action == "attach_to_workitem":
            if not project_id or not workitem_id or not page_id:
                return missing(action, "project_id, workitem_id, page_id")
            try:
                return client.work_items.pages.create(
                    workspace_slug=workspace_slug,
                    project_id=project_id,
                    work_item_id=workitem_id,
                    data=CreateWorkItemPage(page_id=page_id),
                )
            except Exception as e:
                return f"Error attaching page to work item: {str(e)}"

        if action == "detach_from_workitem":
            if not project_id or not workitem_id or not workitem_page_id:
                return missing(action, "project_id, workitem_id, workitem_page_id")
            try:
                client.work_items.pages.delete(
                    workspace_slug=workspace_slug,
                    project_id=project_id,
                    work_item_id=workitem_id,
                    work_item_page_id=workitem_page_id,
                )
                return None
            except Exception as e:
                return f"Error detaching page from work item: {str(e)}"

