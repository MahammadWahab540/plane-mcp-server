"""Projects in a workspace, features, and project-scoped saved views."""

from __future__ import annotations

import json
from typing import Any, Literal, get_args

from fastmcp import FastMCP
from plane.models.enums import TimezoneEnum
from plane.models.projects import (
    CreateProject,
    PaginatedProjectLiteResponse,
    PaginatedProjectMemberResponse,
    Project,
    ProjectFeature,
    ProjectWorklogSummary,
    UpdateProject,
)
from plane.models.query_params import ProjectLiteListQueryParams

from plane_mcp.client import get_plane_client_context
from plane_mcp.toolkit import Action, build_annotations, build_description, missing, needs, opt, plan_gated, rich_text
from plane_mcp.tools.http_helper import get_base_url, make_http_request

NAME = "project"
TITLE = "Projects"

TIMEZONES = get_args(TimezoneEnum)

DEFAULT_PER_PAGE = 100

ACTIONS = (
    Action(
        "list", (), ("cursor", "per_page", "order_by"), note="trimmed fields; use retrieve for full detail", read=True
    ),
    Action("retrieve", ("project_id",), read=True),
    Action(
        "create",
        ("name", "identifier"),
        (
            "description",
            "description_html",
            "project_lead",
            "default_assignee",
            "emoji",
            "cover_image",
            "timezone",
            "archive_in",
            "close_in",
            "external_source",
            "external_id",
        ),
    ),
    Action(
        "update",
        ("project_id",),
        (
            "name",
            "description",
            "description_html",
            "identifier",
            "project_lead",
            "default_assignee",
            "emoji",
            "cover_image",
            "network",
            "timezone",
            "archive_in",
            "close_in",
            "default_state",
            "estimate",
            "is_time_tracking_enabled",
            "external_source",
            "external_id",
        ),
        note="only the fields you pass are changed",
    ),
    Action("delete", ("project_id",), destructive=True),
    Action("archive", ("project_id",)),
    Action("unarchive", ("project_id",)),
    Action("worklog_summary", ("project_id",), read=True),
    Action("get_features", ("project_id",), note="derives features from project.retrieve in Plane v1.4.2", read=True),
    Action(
        "update_features",
        ("project_id",),
        (
            "modules",
            "cycles",
            "views",
            "pages",
            "intakes",
            "workitem_types",
            "epics",
            "parallel_cycles",
            "project_updates",
            "workflows",
        ),
        note="toggles project features on or off",
    ),
    Action("list_views", ("project_id",), ("cursor", "per_page"), note="list saved views (issue-views)", read=True),
    Action("retrieve_view", ("project_id", "view_id"), note="get a saved view", read=True),
    Action(
        "create_view",
        ("project_id", "view_name"),
        (
            "view_description",
            "view_access",
            "view_filters",
            "view_display_filters",
            "view_display_properties",
            "view_rich_filters",
            "view_sort_order",
        ),
        note="create a saved view; JSON fields as strings",
    ),
    Action(
        "update_view",
        ("project_id", "view_id"),
        (
            "view_name",
            "view_description",
            "view_access",
            "view_filters",
            "view_display_filters",
            "view_display_properties",
            "view_rich_filters",
            "view_sort_order",
        ),
        note="update a saved view; only pass fields to change",
    ),
    Action("delete_view", ("project_id", "view_id"), note="delete a saved view", destructive=True),
)

FOOTER = (
    "identifier is the short work item prefix, such as ENG. network is 0 for secret or 2 for public. "
    "project_lead and default_assignee are member ids -- get them from `member list_workspace`. "
    "Feature toggles are booleans; omitted ones are left as they are. "
    "In Plane v1.4.2, get_features derives data from project.retrieve since no separate endpoint exists. "
    "Saved views are Plane v1.4.2 issue-views: view_filters, view_display_filters, view_display_properties, "
    "view_rich_filters are JSON objects; pass as strings or dicts."
)

LEGACY = {
    "list_projects": "list",
    "retrieve_project": "retrieve",
    "create_project": "create",
    "update_project": "update",
    "delete_project": "delete",
    "get_project_worklog_summary": "worklog_summary",
    "update_project_features": "update_features",
}

LEGACY_UNMAPPED = {
    "manage_project_archive": "took archive=bool, which spans two actions: use archive or unarchive",
}


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
        description=build_description("Projects, features, and saved views.", ACTIONS, FOOTER),
        annotations=build_annotations(TITLE, ACTIONS),
    )
    @plan_gated("This project feature")
    def project(
        action: Literal[
            "list",
            "retrieve",
            "create",
            "update",
            "delete",
            "archive",
            "unarchive",
            "worklog_summary",
            "get_features",
            "update_features",
            "list_views",
            "retrieve_view",
            "create_view",
            "update_view",
            "delete_view",
        ],
        project_id: str = "",
        name: str = "",
        identifier: str = "",
        description: str = "",
        description_html: str = "",
        project_lead: str = "",
        default_assignee: str = "",
        emoji: str = "",
        cover_image: str = "",
        network: int | None = None,
        timezone: str = "",
        archive_in: int = 0,
        close_in: int = 0,
        default_state: str = "",
        estimate: str = "",
        external_source: str = "",
        external_id: str = "",
        modules: bool | None = None,
        cycles: bool | None = None,
        views: bool | None = None,
        pages: bool | None = None,
        intakes: bool | None = None,
        workitem_types: bool | None = None,
        epics: bool | None = None,
        parallel_cycles: bool | None = None,
        project_updates: bool | None = None,
        workflows: bool | None = None,
        is_time_tracking_enabled: bool | None = None,
        cursor: str = "",
        per_page: int = 0,
        order_by: str = "",
        view_id: str = "",
        view_name: str = "",
        view_description: str = "",
        view_access: int | None = None,
        view_filters: str = "",
        view_display_filters: str = "",
        view_display_properties: str = "",
        view_rich_filters: str = "",
        view_sort_order: float = 0.0,
    ) -> (
        Project
        | PaginatedProjectLiteResponse
        | PaginatedProjectMemberResponse
        | ProjectFeature
        | dict[str, Any]
        | list[ProjectWorklogSummary]
        | str
        | None
    ):
        client, workspace_slug = get_plane_client_context()

        if timezone and timezone not in TIMEZONES:
            return f"Error: {timezone!r} is not a recognised timezone."
        if network is not None and network not in (0, 2):
            return "Error: network must be 0 (secret) or 2 (public)."
        zone: TimezoneEnum | None = timezone or None  # type: ignore[assignment]

        if action == "list":
            return client.projects.list_lite(
                workspace_slug=workspace_slug,
                params=ProjectLiteListQueryParams(
                    cursor=opt(cursor),
                    per_page=per_page or DEFAULT_PER_PAGE,
                    order_by=opt(order_by),
                    include_archived=False,
                ),
            )

        if action == "create":
            if error := needs(action, name=name, identifier=identifier):
                return error
            return client.projects.create(
                workspace_slug=workspace_slug,
                data=CreateProject(
                    name=name,
                    identifier=identifier,
                    description=opt(description),
                    description_html=rich_text(description_html, description),
                    project_lead=opt(project_lead),
                    default_assignee=opt(default_assignee),
                    emoji=opt(emoji),
                    cover_image=opt(cover_image),
                    module_view=modules,
                    cycle_view=cycles,
                    issue_views_view=views,
                    page_view=pages,
                    intake_view=intakes,
                    archive_in=opt(archive_in),
                    close_in=opt(close_in),
                    timezone=zone,
                    external_source=opt(external_source),
                    external_id=opt(external_id),
                    is_issue_type_enabled=workitem_types,
                ),
            )

        if not project_id:
            return missing(action, "project_id")

        if action == "retrieve":
            return client.projects.retrieve(workspace_slug=workspace_slug, project_id=project_id)

        if action == "update":
            return client.projects.update(
                workspace_slug=workspace_slug,
                project_id=project_id,
                data=UpdateProject(
                    name=opt(name),
                    description=opt(description),
                    description_html=rich_text(description_html, description),
                    identifier=opt(identifier),
                    project_lead=opt(project_lead),
                    default_assignee=opt(default_assignee),
                    emoji=opt(emoji),
                    cover_image=opt(cover_image),
                    network=network,
                    module_view=modules,
                    cycle_view=cycles,
                    issue_views_view=views,
                    page_view=pages,
                    intake_view=intakes,
                    archive_in=opt(archive_in),
                    close_in=opt(close_in),
                    timezone=zone,
                    external_source=opt(external_source),
                    external_id=opt(external_id),
                    is_issue_type_enabled=workitem_types,
                    is_time_tracking_enabled=is_time_tracking_enabled,
                    default_state=opt(default_state),
                    estimate=opt(estimate),
                ),
            )

        if action == "delete":
            client.projects.delete(workspace_slug=workspace_slug, project_id=project_id)
            return None

        if action == "archive":
            client.projects.archive(workspace_slug=workspace_slug, project_id=project_id)
            return None

        if action == "unarchive":
            client.projects.unarchive(workspace_slug=workspace_slug, project_id=project_id)
            return None

        if action == "worklog_summary":
            return client.projects.get_worklog_summary(workspace_slug=workspace_slug, project_id=project_id)

        if action == "get_features":
            try:
                proj = client.projects.retrieve(workspace_slug=workspace_slug, project_id=project_id)
                features = {
                    "module_view": getattr(proj, "module_view", False),
                    "cycle_view": getattr(proj, "cycle_view", False),
                    "issue_views_view": getattr(proj, "issue_views_view", False),
                    "page_view": getattr(proj, "page_view", True),
                    "intake_view": getattr(proj, "intake_view", False),
                    "is_time_tracking_enabled": getattr(proj, "is_time_tracking_enabled", False),
                    "is_issue_type_enabled": getattr(proj, "is_issue_type_enabled", False),
                    "guest_view_all_features": getattr(proj, "guest_view_all_features", False),
                }
                return features
            except Exception as e:
                return f"Error retrieving project features: {str(e)}"

        if action == "update_features":
            return client.projects.update_features(
                workspace_slug=workspace_slug,
                project_id=project_id,
                data=ProjectFeature(
                    modules=modules,
                    cycles=cycles,
                    views=views,
                    pages=pages,
                    intakes=intakes,
                    work_item_types=workitem_types,
                    epics=epics,
                    parallel_cycles=parallel_cycles,
                    project_updates=project_updates,
                    workflows=workflows,
                ),
            )

        # Saved views actions (Plane v1.4.2 issue-views)
        try:
            base_url = get_base_url()
        except ValueError as e:
            return f"Error: {str(e)}"

        if action == "list_views":
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

        if action == "retrieve_view":
            if not view_id:
                return missing(action, "view_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            status, response = make_http_request("GET", path, base_url)
            if status == 200:
                return response
            return f"Error retrieving view: {status} {response}"

        if action == "create_view":
            if not view_name:
                return missing(action, "view_name")

            data = {"name": view_name}
            if view_description:
                data["description"] = view_description
            if view_access is not None:
                data["access"] = view_access

            filters_obj = _parse_json_field(view_filters)
            if filters_obj is not None:
                data["filters"] = filters_obj
            elif view_filters:
                return "Error: view_filters must be valid JSON"

            display_filters_obj = _parse_json_field(view_display_filters)
            if display_filters_obj is not None:
                data["display_filters"] = display_filters_obj
            elif view_display_filters:
                return "Error: view_display_filters must be valid JSON"

            display_properties_obj = _parse_json_field(view_display_properties)
            if display_properties_obj is not None:
                data["display_properties"] = display_properties_obj
            elif view_display_properties:
                return "Error: view_display_properties must be valid JSON"

            rich_filters_obj = _parse_json_field(view_rich_filters)
            if rich_filters_obj is not None:
                data["rich_filters"] = rich_filters_obj
            elif view_rich_filters:
                return "Error: view_rich_filters must be valid JSON"

            if view_sort_order:
                data["sort_order"] = view_sort_order

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/"
            status, response = make_http_request("POST", path, base_url, data=data)
            if status in (200, 201):
                return response
            return f"Error creating view: {status} {response}"

        if action == "update_view":
            if not view_id:
                return missing(action, "view_id")

            has_update = (
                view_name
                or view_description
                or view_access is not None
                or view_filters
                or view_display_filters
                or view_display_properties
                or view_rich_filters
                or view_sort_order
            )
            if not has_update:
                return "Error: provide at least one field to update"

            data = {}
            if view_name:
                data["name"] = view_name
            if view_description:
                data["description"] = view_description
            if view_access is not None:
                data["access"] = view_access

            filters_obj = _parse_json_field(view_filters)
            if filters_obj is not None:
                data["filters"] = filters_obj
            elif view_filters:
                return "Error: view_filters must be valid JSON"

            display_filters_obj = _parse_json_field(view_display_filters)
            if display_filters_obj is not None:
                data["display_filters"] = display_filters_obj
            elif view_display_filters:
                return "Error: view_display_filters must be valid JSON"

            display_properties_obj = _parse_json_field(view_display_properties)
            if display_properties_obj is not None:
                data["display_properties"] = display_properties_obj
            elif view_display_properties:
                return "Error: view_display_properties must be valid JSON"

            rich_filters_obj = _parse_json_field(view_rich_filters)
            if rich_filters_obj is not None:
                data["rich_filters"] = rich_filters_obj
            elif view_rich_filters:
                return "Error: view_rich_filters must be valid JSON"

            if view_sort_order:
                data["sort_order"] = view_sort_order

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            status, response = make_http_request("PATCH", path, base_url, data=data)
            if status == 200:
                return response
            return f"Error updating view: {status} {response}"

        if action == "delete_view":
            if not view_id:
                return missing(action, "view_id")

            path = f"/api/workspaces/{workspace_slug}/projects/{project_id}/issue-views/{view_id}/"
            status, response = make_http_request("DELETE", path, base_url)
            if status in (200, 204):
                return None
            return f"Error deleting view: {status} {response}"

