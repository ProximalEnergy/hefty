import asyncio
import datetime
from typing import Annotated, Any, cast

from core.crud.operational.device_types import get_device_types
from core.crud.operational.issue_categories import get_issue_categories
from core.crud.project import issues as core_project_issues
from core.crud.project.devices import get_project_devices
from core.crud.project.tags import get_project_tags_v2
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query

from app import interfaces
from app.dependencies import get_project_api
from core import models

router = APIRouter(prefix="/issues", tags=["project_issues"])


def _unique_ints(*, rows: list[dict[str, Any]], key: str) -> list[int]:
    """Return sorted unique integer values from a row field.

    Args:
        rows: Row dictionaries to inspect.
        key: Field name containing integer-like values.
    """
    values = {int(row[key]) for row in rows if row.get(key) is not None}
    return sorted(values)


def _build_tag_name_full(
    *,
    tag: dict[str, Any] | None,
    device_name_full: str,
    device_type_name: str,
) -> str | None:
    """Build display name for an issue tag when tag metadata is available.

    Args:
        tag: Tag row containing deep sensor type fields.
        device_name_full: Display name for the issue device.
        device_type_name: Display name for the issue device type.
    """
    if tag is None:
        return None

    sensor_type_name = str(tag.get("sensor_type_name_long") or "").strip()
    if not sensor_type_name:
        return device_name_full

    device_type_prefix = f"{device_type_name} "
    if sensor_type_name.startswith(device_type_prefix):
        sensor_type_name = sensor_type_name.removeprefix(device_type_prefix)

    return f"{device_name_full} {sensor_type_name}".strip()


@router.get("", response_model=list[interfaces.ProjectIssueSummary])
async def get_project_issues_route(
    project: Annotated[models.Project, Depends(get_project_api)],
    active_only: bool = True,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    issue_category_ids: Annotated[list[int] | None, Query()] = None,
) -> list[interfaces.ProjectIssueSummary]:
    """Retrieve project issues for the impacts page.

    Args:
        project: Project model from dependency injection.
        active_only: Include only unresolved issues when true.
        start: Include issues active at or after this timestamp.
        end: Include issues active at or before this timestamp.
        device_ids: Device ids to include.
        issue_category_ids: Issue category ids to include.
    """
    issues_df = await core_project_issues.get_issues(
        device_ids=device_ids,
        open_only=active_only,
        issue_category_ids=issue_category_ids,
        window_start=start,
        window_end=end,
    ).get_async(
        schema=project.name_short,
        output_type=OutputType.POLARS,
    )
    if issues_df is None or issues_df.is_empty():
        return []

    issue_rows = issues_df.to_dicts()
    device_ids = _unique_ints(rows=issue_rows, key="device_id")
    issue_category_ids = _unique_ints(rows=issue_rows, key="issue_category_id")
    tag_ids = _unique_ints(rows=issue_rows, key="tag_id")

    devices_task = (
        get_project_devices(device_ids=device_ids).get_async(
            schema=project.name_short,
            output_type=OutputType.POLARS,
        )
        if device_ids
        else asyncio.sleep(0, result=cast(Any, None))
    )
    issue_categories_task = (
        get_issue_categories(
            issue_category_ids=issue_category_ids,
        ).get_async(output_type=OutputType.POLARS)
        if issue_category_ids
        else asyncio.sleep(0, result=cast(Any, None))
    )
    tags_task = (
        get_project_tags_v2(
            tag_ids=tag_ids,
            deep=True,
            include_ghost_tags=True,
        ).get_async(
            schema=project.name_short,
            output_type=OutputType.POLARS,
        )
        if tag_ids
        else asyncio.sleep(0, result=cast(Any, None))
    )

    devices_df, issue_categories_df, tags_df = await asyncio.gather(
        devices_task,
        issue_categories_task,
        tags_task,
    )
    device_rows = (
        devices_df.to_dicts()
        if devices_df is not None and not devices_df.is_empty()
        else []
    )
    devices_by_id = {
        int(device["device_id"]): device
        for device in device_rows
        if device.get("device_id") is not None
    }

    device_type_ids = _unique_ints(rows=device_rows, key="device_type_id")
    device_types_df = (
        await get_device_types(
            device_type_ids=device_type_ids,
        ).get_async(output_type=OutputType.POLARS)
        if device_type_ids
        else None
    )
    device_type_rows = (
        device_types_df.to_dicts()
        if device_types_df is not None and not device_types_df.is_empty()
        else []
    )
    device_type_names = {
        int(device_type["device_type_id"]): str(device_type["name_long"])
        for device_type in device_type_rows
        if device_type.get("device_type_id") is not None
    }

    issue_category_rows = (
        issue_categories_df.to_dicts()
        if issue_categories_df is not None and not issue_categories_df.is_empty()
        else []
    )
    issue_category_names = {
        int(category["issue_category_id"]): str(category["name_long"])
        for category in issue_category_rows
        if category.get("issue_category_id") is not None
    }

    tag_rows = (
        tags_df.to_dicts() if tags_df is not None and not tags_df.is_empty() else []
    )
    tags_by_id = {
        int(tag["tag_id"]): tag for tag in tag_rows if tag.get("tag_id") is not None
    }

    summaries: list[interfaces.ProjectIssueSummary] = []
    for issue in issue_rows:
        device = devices_by_id.get(int(issue["device_id"]))
        device_type_id = (
            int(device["device_type_id"])
            if device is not None and device.get("device_type_id") is not None
            else None
        )
        device_type_name = (
            device_type_names.get(device_type_id, "Unknown")
            if device_type_id is not None
            else "Unknown"
        )
        device_name = str(device.get("name_long") or "") if device else ""
        device_name_full = f"{device_type_name} {device_name}".strip()
        tag_id = int(issue["tag_id"]) if issue.get("tag_id") is not None else None
        tag = tags_by_id.get(tag_id) if tag_id is not None else None
        category_id = int(issue["issue_category_id"])

        summaries.append(
            interfaces.ProjectIssueSummary(
                issue_id=int(issue["issue_id"]),
                device_id=int(issue["device_id"]),
                device_type_id=device_type_id,
                device_type_name=device_type_name,
                device_name_full=device_name_full,
                tag_id=tag_id,
                tag_name_full=_build_tag_name_full(
                    tag=tag,
                    device_name_full=device_name_full,
                    device_type_name=device_type_name,
                ),
                issue_category_id=category_id,
                issue_category=issue_category_names.get(category_id, "Unknown"),
                time_start=issue["time_start"],
                time_end=issue.get("time_end"),
            )
        )

    return summaries


@router.get("/issue-devices")
async def get_issue_devices(
    project: Annotated[models.Project, Depends(get_project_api)],
) -> dict[str, list[dict[str, int | str]]]:
    """Retrieve unique device types and devices with associated issues.

    Args:
        project: Project model from dependency injection.
    """
    issue_devices_df = await core_project_issues.get_issue_devices_summary().get_async(
        schema=project.name_short,
        output_type=OutputType.POLARS,
    )
    if issue_devices_df is None or issue_devices_df.is_empty():
        return {"unique_types": [], "unique_devices": []}

    unique_type_names: dict[int, str] = {}
    unique_device_names: dict[int, str] = {}
    for row in issue_devices_df.to_dicts():
        device_type_id = row.get("device_type_id")
        if device_type_id is None:
            continue
        device_type_name = str(row.get("device_type_name") or "Unknown")
        unique_type_names[int(device_type_id)] = device_type_name

        device_id = row.get("device_id")
        if device_id is None:
            continue
        device_name = str(row.get("device_name") or "")
        unique_device_names[int(device_id)] = (
            f"{device_type_name} {device_name}".strip()
        )

    return {
        "unique_types": [
            {"device_type_id": device_type_id, "device_type_name": device_type_name}
            for device_type_id, device_type_name in sorted(unique_type_names.items())
        ],
        "unique_devices": [
            {"device_id": device_id, "device_name_full": device_name_full}
            for device_id, device_name_full in sorted(unique_device_names.items())
        ],
    }
