"""HTTP client for Proximal operational API (replaces vendored api client)."""

import os
from typing import cast

import httpx

_DEFAULT_BASE_URL = "https://api.proximal.energy"


def _api_key() -> str:
    key = os.getenv("PROXIMAL_API_KEY")
    if not key:
        msg = "PROXIMAL_API_KEY is not set"
        raise ValueError(msg)
    return key


def _base_url() -> str:
    return os.getenv("PROXIMAL_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _operational_url(*, project_id: str, path: str) -> str:
    return f"{_base_url()}/v1/operational/projects/{project_id}{path}"


def get_project_metadata(*, project_id: str) -> dict:
    """Fetch project metadata.

    Args:
        project_id: Project UUID string.

    Returns:
        Project JSON object.
    """
    url = _operational_url(project_id=project_id, path="")
    response = httpx.get(
        url,
        headers={"x-api-key": _api_key()},
        timeout=60.0,
    )
    response.raise_for_status()
    return cast(dict, response.json())


def get_devices(
    *,
    project_id: str,
    device_type_ids: list[int] | None = None,
    device_id_descendent_of: int | None = None,
    name_short: str = "",
) -> list[dict]:
    """Fetch filtered devices for a project.

    Args:
        project_id: Project UUID string.
        device_type_ids: Optional device type IDs to include.
        device_id_descendent_of: Optional ancestor device ID.
        name_short: Optional exact short name filter.

    Returns:
        List of device JSON objects.
    """
    url = _operational_url(project_id=project_id, path="/devices")
    filters: dict[str, object] = {}
    if device_type_ids:
        filters["device_type_ids"] = device_type_ids
    if device_id_descendent_of is not None:
        filters["device_id_descendent_of"] = device_id_descendent_of
    if name_short:
        filters["name_short"] = name_short
    response = httpx.post(
        url,
        json=filters,
        headers={"x-api-key": _api_key()},
        timeout=120.0,
    )
    response.raise_for_status()
    return cast(list[dict], response.json())
