from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.v1.operational.project.project_cmms_tickets import get_cmms_tickets


@pytest.mark.asyncio
async def test_get_cmms_tickets_no_permissions():
    """Test get_cmms_tickets when user has no CMMS permissions."""

    # Mock dependencies
    mock_db = AsyncMock()
    mock_project_db = MagicMock()
    mock_user = MagicMock()
    mock_user.company_id = uuid4()

    project_id = uuid4()

    # Mock the get_cmms_permissions_by_project_id to return empty list
    with patch(
        "app.v1.operational.project.project_cmms_tickets.get_cmms_permissions_by_project_id"
    ) as mock_get_permissions:
        mock_get_permissions.return_value = []

        # Call the function
        result = await get_cmms_tickets(
            project_id=project_id,
            db=mock_db,
            project_db=mock_project_db,
            user=mock_user,
        )

    # Assert the result
    assert result.metadata.integration_configured is False
    assert result.data == []

    # Verify the mock was called correctly
    mock_get_permissions.assert_called_once_with(
        db=mock_db,
        company_id=mock_user.company_id,
        project_id=project_id,
        can_view=True,
    )
