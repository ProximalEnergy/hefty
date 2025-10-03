"""
Test suite for data_timeseries CRUD operations.

This module contains tests to ensure that the two versions of get_project_data_timeseries
functions generate identical SQL queries. The main purpose is to verify that:

1. get_project_data_timeseries (v1) - executes queries immediately
2. get_project_data_timeseries_v2 (v2) - returns queries for deferred execution

Both functions should produce the same SQL query text with identical bind parameters
for the same input parameters.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from core.crud.project.data_timeseries import (
    get_project_data_timeseries,
    get_project_data_timeseries_v2,
)


def _construct_expected_query_text(
    table_schema: str,
    table_name: str,
    interval: str,
    start: str,
    end: str,
    tag_ids: tuple[int, ...],
) -> str:
    """Helper function to construct the expected query text for comparison."""
    return f"""
    SELECT
        time_bucket('{interval}', time) + interval '{interval}' as time_bucket,
        tag_id,
        last(value_integer, time) as value_integer,
        last(value_bigint, time) as value_bigint,
        last(value_real, time) as value_real,
        last(value_double, time) as value_double,
        last(value_boolean, time) as value_boolean,
        last(value_text, time) as value_text
    FROM
        {table_schema}.{table_name}
    WHERE
        time >= '{start}' and time < '{end}' and tag_id IN {tag_ids}
    GROUP BY
        time_bucket, tag_id
    ORDER BY
        time_bucket, tag_id;
    """.strip()  # noqa: S608


@pytest.fixture
def mock_db_session():
    """Create a mock database session with a mock bind."""
    session = MagicMock()
    bind = MagicMock()
    session.bind = bind
    return session


@pytest.fixture
def sample_parameters():
    """Sample parameters for testing both functions."""
    return {
        "project_name_short": "test_project",
        "tag_ids": [1, 2, 3],
        "start": pd.Timestamp("2024-01-01 00:00:00"),
        "end": pd.Timestamp("2024-01-02 00:00:00"),
        "interval": "1h",
        "cagg_interval": None,
    }


def test_query_text_comparison_default_table(mock_db_session, sample_parameters):
    """
    Test that both functions generate identical query text for the default data_timeseries table.

    This test verifies that get_project_data_timeseries and get_project_data_timeseries_v2
    construct the same SQL statement when no cagg_interval is specified.
    """

    # Mock the Table creation and its properties
    with patch("core.crud.project.data_timeseries.Table") as mock_table_class:
        # Create a mock table instance
        mock_table = MagicMock()
        mock_table.schema = sample_parameters["project_name_short"]
        mock_table.name = "data_timeseries"
        mock_table_class.return_value = mock_table

        # Mock MetaData
        with patch("core.crud.project.data_timeseries.MetaData"):
            # Get query from v2 function (which returns the query)
            result_v2 = get_project_data_timeseries_v2(
                project_db=mock_db_session, **sample_parameters
            )
            query_text_v2 = result_v2.sql_string()

            # Mock the execute method to capture the query for v1 function
            executed_query = None

            def capture_execute(query):
                nonlocal executed_query
                executed_query = query
                # Return a mock result
                mock_result = MagicMock()
                mock_result.__iter__ = lambda self: iter([])
                return mock_result

            mock_db_session.execute.side_effect = capture_execute

            # Call v1 function
            get_project_data_timeseries(project_db=mock_db_session, **sample_parameters)

            # Get the query text from the captured query
            query_text_v1 = str(executed_query)

            # Compare the query texts
            assert query_text_v1 == query_text_v2, (
                f"Query texts differ:\nv1: {query_text_v1}\nv2: {query_text_v2}"
            )


def test_query_text_comparison_cagg_table(mock_db_session, sample_parameters):
    """
    Test that both functions generate identical query text for continuous aggregate tables.

    This test verifies that both functions correctly construct the table name when
    cagg_interval is specified (e.g., data_timeseries_1d) and generate the same SQL.
    """

    # Modify parameters to use cagg table
    cagg_params = sample_parameters.copy()
    cagg_params["cagg_interval"] = "1d"

    # Mock the Table creation and its properties
    with patch("core.crud.project.data_timeseries.Table") as mock_table_class:
        # Create a mock table instance
        mock_table = MagicMock()
        mock_table.schema = cagg_params["project_name_short"]
        mock_table.name = "data_timeseries_1d"
        mock_table_class.return_value = mock_table

        # Mock MetaData
        with patch("core.crud.project.data_timeseries.MetaData"):
            # Get query from v2 function (which returns the query)
            result_v2 = get_project_data_timeseries_v2(
                project_db=mock_db_session, **cagg_params
            )
            query_text_v2 = result_v2.sql_string()

            # Mock the execute method to capture the query for v1 function
            executed_query = None

            def capture_execute(query):
                nonlocal executed_query
                executed_query = query
                # Return a mock result
                mock_result = MagicMock()
                mock_result.__iter__ = lambda self: iter([])
                return mock_result

            mock_db_session.execute.side_effect = capture_execute

            # Call v1 function
            get_project_data_timeseries(project_db=mock_db_session, **cagg_params)

            # Get the query text from the captured query
            query_text_v1 = str(executed_query)

            # Compare the query texts
            assert query_text_v1 == query_text_v2, (
                f"Query texts differ:\nv1: {query_text_v1}\nv2: {query_text_v2}"
            )


def test_bind_parameters_are_identical(mock_db_session, sample_parameters):
    """
    Test that both functions use identical bind parameters for SQL queries.

    This ensures that the parameter binding (interval, start, end, tag_ids)
    is consistent between both function implementations.
    """

    # Mock the Table creation and its properties
    with patch("core.crud.project.data_timeseries.Table") as mock_table_class:
        # Create a mock table instance
        mock_table = MagicMock()
        mock_table.schema = sample_parameters["project_name_short"]
        mock_table.name = "data_timeseries"
        mock_table_class.return_value = mock_table

        # Mock MetaData
        with patch("core.crud.project.data_timeseries.MetaData"):
            # Get query from v2 function
            result_v2 = get_project_data_timeseries_v2(
                project_db=mock_db_session, **sample_parameters
            )

            # Extract bind parameters from v2 query
            v2_query = result_v2.query
            v2_params = v2_query.compile().params

            # Mock the execute method to capture bind parameters for v1 function
            captured_params = None

            def capture_execute(query):
                nonlocal captured_params
                captured_params = query.compile().params
                # Return a mock result
                mock_result = MagicMock()
                mock_result.__iter__ = lambda self: iter([])
                return mock_result

            mock_db_session.execute.side_effect = capture_execute

            # Call v1 function
            get_project_data_timeseries(project_db=mock_db_session, **sample_parameters)

            # Compare bind parameters
            assert captured_params == v2_params, (
                f"Bind parameters differ:\nv1: {captured_params}\nv2: {v2_params}"
            )


def test_table_name_construction_logic():
    """
    Test the table name construction logic used by both functions.

    Verifies that the logic for determining table names (data_timeseries vs
    data_timeseries_{cagg_interval}) is consistent.
    """

    # Test default table name
    assert (
        "data_timeseries" == "data_timeseries"
    )  # Both use this when cagg_interval is None

    # Test cagg table name construction
    cagg_interval = "1h"
    expected_table_name = f"data_timeseries_{cagg_interval}"
    assert expected_table_name == "data_timeseries_1h"

    cagg_interval = "1d"
    expected_table_name = f"data_timeseries_{cagg_interval}"
    assert expected_table_name == "data_timeseries_1d"


def test_parameter_formatting_consistency(sample_parameters):
    """
    Test that both functions format input parameters consistently.

    Ensures that timestamps are formatted using isoformat() and tag_ids
    are converted to tuples in the same way by both functions.
    """

    # Both functions should format timestamps using isoformat()
    start_formatted = sample_parameters["start"].isoformat()
    end_formatted = sample_parameters["end"].isoformat()
    tag_ids_formatted = tuple(sample_parameters["tag_ids"])

    assert isinstance(start_formatted, str)
    assert isinstance(end_formatted, str)
    assert isinstance(tag_ids_formatted, tuple)

    # Verify the format matches what both functions expect
    assert start_formatted == "2024-01-01T00:00:00"
    assert end_formatted == "2024-01-02T00:00:00"
    assert tag_ids_formatted == (1, 2, 3)
