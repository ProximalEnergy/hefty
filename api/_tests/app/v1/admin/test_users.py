import uuid

import pandas as pd
import pytest
from app.interfaces import UserAuthed
from app.v1.admin import users as users_route
from core.db_query import OutputType
from core.enumerations import UserTypeEnum

REQUESTER_COMPANY_ID = uuid.uuid4()
FOREIGN_COMPANY_ID = uuid.uuid4()
REQUESTED_USER_ID = "user_foreign"


class FakeUsersQuery:
    """Fake user query that leaks the foreign user when unscoped."""

    def __init__(self, *, company_ids: list[uuid.UUID] | None) -> None:
        """Store the company scope from the route.

        Args:
            company_ids: Company IDs passed to the user query.
        """
        self.company_ids = company_ids

    async def get_async(self, *, output_type: OutputType) -> pd.DataFrame:
        """Return user rows for the requested output type.

        Args:
            output_type: Output format requested by the route.
        """
        assert output_type == OutputType.PANDAS
        if self.company_ids == [REQUESTER_COMPANY_ID]:
            return pd.DataFrame(
                columns=[
                    "user_id",
                    "user_type_id",
                    "company_id",
                    "name_long",
                    "api_key",
                    "project_ids",
                ]
            )

        return pd.DataFrame(
            [
                {
                    "user_id": REQUESTED_USER_ID,
                    "user_type_id": UserTypeEnum.USER,
                    "company_id": FOREIGN_COMPANY_ID,
                    "name_long": "Foreign User",
                    "api_key": None,
                    "project_ids": None,
                }
            ]
        )


@pytest.mark.asyncio
async def test_get_users_by_user_id_scopes_non_superadmin_to_own_company(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-superadmins cannot use user_ids to read across company boundaries.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    calls: list[tuple[list[uuid.UUID] | None, list[str] | None]] = []

    def fake_get_users(
        *,
        company_ids: list[uuid.UUID] | None = None,
        user_ids: list[str] | None = None,
    ) -> FakeUsersQuery:
        calls.append((company_ids, user_ids))
        return FakeUsersQuery(company_ids=company_ids)

    monkeypatch.setattr(users_route, "get_users", fake_get_users)

    response = await users_route.get_users_route(
        user_data=UserAuthed(
            user_id="user_requester",
            company_id=REQUESTER_COMPANY_ID,
            public_metadata={},
            operational_project_ids=[],
            user_type_id=UserTypeEnum.USER,
            authentication_method="jwt",
        ),
        company_ids=None,
        user_ids=[REQUESTED_USER_ID],
        include_image_urls=False,
    )

    assert response == []
    assert calls == [([REQUESTER_COMPANY_ID], [REQUESTED_USER_ID])]
