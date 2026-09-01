"""Pages, at workspace or project scope, their hierarchy, and their links to work items.

Every page action is scoped by whether project_id is supplied: with it the page
is a project page, without it a workspace page. The SDK has a separate endpoint
pair for each, so the branch is explicit rather than a default.

Note: Plane v1.4.2 does not support workspace-level pages. Only project pages are available.
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP
from plane.models.pages import CreatePage, Page, UpdatePage
from plane.models.query_params import PaginatedQueryParams
from plane.models.work_item_pages import CreateWorkItemPage, WorkItemPage

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import Action, as_params, build_annotations, build_description, envelope, missing, needs, opt

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
        ("name", "description_html"),
        (
            "project_id",
            "parent_id",
            "access",
            "color",
            "is_locked",
            "external_source",
            "external_id",
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
        ("project_id", "archive"),
        note="project pages only; archive defaults to true",
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
    "Plane v1.4.2 supports project pages only; workspace pages and collections not available. "
    "parent_id is fixed at creation; pass it to build a hierarchy."
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
        parent_id: str = "",
        workitem_id: str = "",
        workitem_page_id: str = "",
        name: str = "",
        description_html: str = "",
        access: int | None = None,
        color: str = "",
        is_locked: bool | None = None,
        archive: bool = True,
        external_source: str = "",
        external_id: str = "",
        cursor: str = "",
        per_page: int = 0,
    ) -> Page | WorkItemPage | list[WorkItemPage] | dict[str, Any] | str | None:
        client, workspace_slug = get_plane_client_context()

        # Workspace page actions are not supported in Plane v1.4.2
        if action in ("list", "retrieve", "create", "update", "archive", "delete") and not project_id:
            return (
                "Error: Workspace-level pages are not supported in Plane v1.4.2. "
                "Provide project_id to use project pages."
            )

        if action == "list":
            params = as_params(PaginatedQueryParams, cursor=cursor, per_page=per_page)
            response = client.pages.list_project_pages(
                workspace_slug=workspace_slug, project_id=project_id, params=params
            )
            return envelope(response)

        if action == "retrieve":
            if not page_id:
                return missing(action, "page_id")
            return client.pages.retrieve_project_page(
                workspace_slug=workspace_slug, project_id=project_id, page_id=page_id
            )

        if action == "archive":
            if not page_id:
                return missing(action, "page_id")
            mover = (
                client.pages.archive_project_page if archive else client.pages.unarchive_project_page
            )
            mover(workspace_slug=workspace_slug, project_id=project_id, page_id=page_id)
            return {"page_id": page_id, "archived": archive}

        if action in ("update", "delete"):
            if not page_id:
                return missing(action, "page_id")
            if action == "delete":
                client.pages.delete_project_page(
                    workspace_slug=workspace_slug, project_id=project_id, page_id=page_id
                )
                return None
            if not (name or description_html):
                return missing(action, "name or description_html")
            return client.pages.update_project_page(
                workspace_slug=workspace_slug,
                project_id=project_id,
                page_id=page_id,
                data=UpdatePage(name=opt(name), description_html=opt(description_html)),
            )

        if action == "create":
            if error := needs(action, name=name, description_html=description_html):
                return error
            if not project_id:
                return "Error: project_id is required for page creation"
            data = CreatePage(
                name=name,
                description_html=description_html,
                access=access,
                color=opt(color),
                is_locked=is_locked,
                parent_id=opt(parent_id),
                external_id=opt(external_id),
                external_source=opt(external_source),
            )
            return client.pages.create_project_page(
                workspace_slug=workspace_slug, project_id=project_id, data=data
            )

        if error := needs(action, project_id=project_id, workitem_id=workitem_id):
            return error

        if action == "list_workitem_pages":
            response = client.work_items.pages.list(
                workspace_slug=workspace_slug, project_id=project_id, work_item_id=workitem_id
            )
            return response.results

        if action == "attach_to_workitem":
            if not page_id:
                return missing(action, "page_id")
            return client.work_items.pages.create(
                workspace_slug=workspace_slug,
                project_id=project_id,
                work_item_id=workitem_id,
                data=CreateWorkItemPage(page_id=page_id),
            )

        if not workitem_page_id:
            return missing(action, "workitem_page_id")
        client.work_items.pages.delete(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=workitem_id,
            work_item_page_id=workitem_page_id,
        )
        return None

