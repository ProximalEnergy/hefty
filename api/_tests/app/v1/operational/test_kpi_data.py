import datetime
import uuid
from typing import Any

import pytest
from app.interfaces import UserAuthed
from app.v1.operational import kpi_data as kpi_data_route
from core.enumerations import UserTypeEnum


@pytest.mark.asyncio
async def test_get_kpi_data_route_scopes_omitted_projects_to_user_projects(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted project filters must stay within the caller's project scope.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    accessible_project_id = uuid.uuid4()
    captured_project_ids: list[list[uuid.UUID] | None] = []

    async def fake_get_kpi_data_helper(
        *,
        start: datetime.date,
        end: datetime.date,
        project_ids: list[uuid.UUID] | None,
        kpi_type_ids: list[int],
        include_device_data: bool,
        include_all_dates: bool = True,
    ) -> list[dict[str, Any]]:
        captured_project_ids.append(project_ids)
        return []

    monkeypatch.setattr(
        kpi_data_route,
        "get_kpi_data_helper",
        fake_get_kpi_data_helper,
    )

    response = await kpi_data_route.get_kpi_data_route(
        user_data=UserAuthed(
            user_id="user_requester",
            company_id=uuid.uuid4(),
            public_metadata={},
            operational_project_ids=[accessible_project_id],
            user_type_id=UserTypeEnum.USER,
            authentication_method="jwt",
        ),
        start=datetime.date(2026, 1, 1),
        end=datetime.date(2026, 1, 2),
        project_ids=None,
        kpi_type_ids=[],
        include_device_data=True,
        include_all_dates=True,
    )

    assert response == []
    assert captured_project_ids == [[accessible_project_id]]


@pytest.mark.asyncio
async def test_get_kpi_data_route_preserves_superadmin_omitted_projects(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Superadmin omitted project filters must preserve all-project semantics.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    captured_project_ids: list[list[uuid.UUID] | None] = []

    async def fake_get_kpi_data_helper(
        *,
        start: datetime.date,
        end: datetime.date,
        project_ids: list[uuid.UUID] | None,
        kpi_type_ids: list[int],
        include_device_data: bool,
        include_all_dates: bool = True,
    ) -> list[dict[str, Any]]:
        captured_project_ids.append(project_ids)
        return []

    monkeypatch.setattr(
        kpi_data_route,
        "get_kpi_data_helper",
        fake_get_kpi_data_helper,
    )

    response = await kpi_data_route.get_kpi_data_route(
        user_data=UserAuthed(
            user_id="superadmin_requester",
            company_id=uuid.uuid4(),
            public_metadata={},
            operational_project_ids=[],
            user_type_id=UserTypeEnum.SUPERADMIN,
            authentication_method="jwt",
        ),
        start=datetime.date(2026, 1, 1),
        end=datetime.date(2026, 1, 2),
        project_ids=None,
        kpi_type_ids=[],
        include_device_data=True,
        include_all_dates=True,
    )

    assert response == []
    assert captured_project_ids == [None]


@pytest.mark.asyncio
async def test_get_kpi_data_helper_returns_no_data_for_empty_project_scope(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty project scopes must not execute an unfiltered KPI query.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """

    def fail_core_get_kpi_data(**kwargs: object) -> None:
        raise AssertionError("empty project scope must not query KPI data")

    monkeypatch.setattr(kpi_data_route, "core_get_kpi_data", fail_core_get_kpi_data)

    response = await kpi_data_route.get_kpi_data_helper(
        start=datetime.date(2026, 1, 1),
        end=datetime.date(2026, 1, 2),
        project_ids=[],
        kpi_type_ids=[],
        include_device_data=True,
    )

    assert response == []
