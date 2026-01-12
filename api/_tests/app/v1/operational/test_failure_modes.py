from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from app.v1.operational.failure_modes import get_failure_modes_route
from core.db_query import OutputType


@pytest.mark.asyncio
async def test_get_failure_modes_route():
    """Test that the route returns a list of failure modes."""
    # Mock data
    mock_df = pd.DataFrame([{"failure_mode_id": 1, "name_short": "Test"}])
    expected_result = mock_df.to_dict(orient="records")

    # Mock DbQuery
    mock_db_query = MagicMock()
    mock_db_query.get_async = AsyncMock(return_value=mock_df)

    with patch(
        "app.v1.operational.failure_modes.get_failure_modes",
        return_value=mock_db_query,
    ) as _:
        result = await get_failure_modes_route(failure_mode_ids=[])

        # Verify result
        assert result == expected_result

        # Verify get_async called with OutputType.PANDAS
        mock_db_query.get_async.assert_called_once_with(output_type=OutputType.PANDAS)
