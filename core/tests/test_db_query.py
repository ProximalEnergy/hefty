from unittest.mock import MagicMock

import sqlalchemy as sa
from core.db_query import DbQuery, OutputType

from core import models


def test_non_select_scalar_executable_returns_scalar_value():
    """Non-select scalar DML returns the returned ORM scalar."""
    stmt = sa.insert(models.Team).returning(models.Team)
    expected_team = object()
    scalar_result = MagicMock()
    unique_result = MagicMock()
    result = MagicMock()
    executor = MagicMock()

    unique_result.one_or_none.return_value = expected_team
    scalar_result.unique.return_value = unique_result
    result.returns_rows = True
    result.scalars.return_value = scalar_result
    executor.execute.return_value = result

    query = DbQuery(query=stmt, is_scalar=True)
    team = query.get(executor=executor, output_type=OutputType.SQLALCHEMY)

    assert team is expected_team
    result.scalars.assert_called_once_with()
    result.mappings.assert_not_called()


def test_text_clause_scalar_keeps_mapping_result():
    """Text clause scalar DML keeps row mapping output."""
    stmt = sa.text("insert into teams default values returning team_id")
    expected_row = {"team_id": "test-team-id"}
    mapping_result = MagicMock()
    result = MagicMock()
    executor = MagicMock()

    mapping_result.one_or_none.return_value = expected_row
    result.returns_rows = True
    result.mappings.return_value = mapping_result
    executor.execute.return_value = result

    query = DbQuery(query=stmt, is_scalar=True)
    row = query.get(executor=executor, output_type=OutputType.SQLALCHEMY)

    assert row == expected_row
    result.mappings.assert_called_once_with()
    result.scalars.assert_not_called()
