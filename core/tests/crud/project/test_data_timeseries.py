"""Contract tests for `DataTimeseries.get()`."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.enumerations import ProjectDatabaseProvider
from polars.testing import assert_frame_equal


def test_get_returns_expected_dataframe_for_clickhouse_page():
    """Lock the current observable `get()` output for a fixed input."""
    epoch_seconds = [
        1_704_096_000,
        1_704_074_400,
        1_704_099_600,
        1_704_078_000,
        1_704_088_800,
        1_704_081_600,
        1_704_092_400,
        1_704_067_200,
        1_704_085_200,
        1_704_070_800,
    ]
    values = [13, 4, 15, 5, 9, 6, 11, 1, 7, 3]

    async def run_case() -> DataTimeseries:
        timeseries = DataTimeseries(
            project_name_short="test_project",  # allow: hardcoded-name-short
            filter_method=FilterMethod.TAG_IDS,
            filter_values=[1],
            query_start=datetime(2024, 1, 1),
            query_end=datetime(2024, 1, 2),
            project_db=MagicMock(),
            ensure_full_range=False,
            ffill_limit=0,
        )
        timeseries._database_provider = ProjectDatabaseProvider.CLICKHOUSE
        timeseries._project_id_int = 123
        timeseries._time_zone = "UTC"
        timeseries._tag_ids = [1]
        timeseries._tags_lut = pl.DataFrame(
            {
                "tag_id": [1],
                "pg_data_type_id": [1],
                "unit_scale": [1.0],
                "unit_offset": [0.0],
            }
        )
        timeseries._tag_dtype_by_id = {}

        client = MagicMock()
        client.query_df_arrow.return_value = pl.DataFrame(
            {
                "time_bucket": pl.Series(epoch_seconds, dtype=pl.UInt32),
                "tag_id": [1] * len(epoch_seconds),
                "value_integer": values,
            }
        )

        with (
            patch.object(
                DataTimeseries,
                "_prepare",
                AsyncMock(return_value=True),
            ),
            patch.object(
                DataTimeseries,
                "_fetch_provider_lookback",
                AsyncMock(return_value=pl.DataFrame()),
            ),
            patch.object(
                DataTimeseries,
                "_build_data_timeseries_query_clickhouse",
                return_value="SELECT 1",
            ),
            patch.object(
                DataTimeseries,
                "_get_clickhouse_client",
                return_value=client,
            ),
        ):
            return await timeseries.get()

    result = asyncio.run(run_case())

    expected = pl.DataFrame(
        {
            "time": pl.Series(
                [
                    datetime(2024, 1, 1, 0, 0),
                    datetime(2024, 1, 1, 1, 0),
                    datetime(2024, 1, 1, 2, 0),
                    datetime(2024, 1, 1, 3, 0),
                    datetime(2024, 1, 1, 4, 0),
                    datetime(2024, 1, 1, 5, 0),
                    datetime(2024, 1, 1, 6, 0),
                    datetime(2024, 1, 1, 7, 0),
                    datetime(2024, 1, 1, 8, 0),
                    datetime(2024, 1, 1, 9, 0),
                ],
                dtype=pl.Datetime(time_unit="us", time_zone="UTC"),
            ),
            "1": [1.0, 3.0, 4.0, 5.0, 6.0, 7.0, 9.0, 11.0, 13.0, 15.0],
        }
    )

    assert_frame_equal(result.df, expected)
    assert result.page_limit_reached is False
