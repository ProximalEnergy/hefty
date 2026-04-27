# test_crud.py
import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pandas as pd
import polars as pl
import pytest
from core.crud.operational.projects import JOINED_PROJECT_TYPE, get_project
from core.db_query import DbQuery, OutputType
from core.enumerations import DeviceType, ProjectType, SensorType
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Load
from sqlalchemy.orm.strategy_options import _LoadElement

from core import models

# ... (Keep Mock classes, EXPECTED_PROJECT_DATA, TEST_PROJECT_ID) ...
TEST_PROJECT_ID = UUID("043fecf7-6cce-4228-acda-b1f23fd6d5f5")


# --- Mock Classes (MockPoint, MockPolygon, MockProjectSpec, MockProjectType,
# MockProject) ---
# (Keep these as they were defined in the previous correct version)
class MockPoint:
    """todo"""

    def __init__(  # nosemgrep: python-enforce-keyword-only-args
        self, type, coordinates
    ):
        """todo"""
        self.type, self.coordinates = type, coordinates

    def __eq__(self, other):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        return (
            isinstance(other, MockPoint)
            and self.type == other.type
            and self.coordinates == other.coordinates
        )


class MockPolygon:
    """todo"""

    def __init__(  # nosemgrep: python-enforce-keyword-only-args
        self, type, coordinates
    ):
        """todo"""
        self.type, self.coordinates = type, coordinates

    def __eq__(self, other):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        return (
            isinstance(other, MockPolygon)
            and self.type == other.type
            and self.coordinates == other.coordinates
        )


class MockProjectSpec:
    """todo"""

    def __init__(self, **kwargs):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        self.__dict__.update(kwargs)

    def __eq__(self, other):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        return isinstance(other, MockProjectSpec) and self.__dict__ == other.__dict__


class MockProjectType:
    """todo"""

    def __init__(self, **kwargs):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        self.__dict__.update(kwargs)

    def __eq__(self, other):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        return isinstance(other, MockProjectType) and self.__dict__ == other.__dict__


class MockProject:
    """todo"""

    def __init__(self, **kwargs):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __eq__(self, other):  # nosemgrep: python-enforce-keyword-only-args
        """todo"""
        return isinstance(other, MockProject) and self.__dict__ == other.__dict__


EXPECTED_PROJECT_DATA = {
    "project_id": TEST_PROJECT_ID,
    "project_type_id": 3,
    "name_short": "serrano",
    "name_long": "Serrano",
    "data_table": "data_timeseries",
    "data_interval": "mqtt",
    "data_cagg_interval": None,
    "address": "Pima/Pinal County, AZ",
    "image_url": None,
    "point": MockPoint(
        type="Point",
        coordinates=[-111.30213385452477, 32.49203885358152],
    ),
    "polygon": MockPolygon(
        type="MultiPolygon",
        coordinates=[(((-111.29508399187915, 32.48720229734512),),)],
    ),
    "elevation": 578.0,
    "time_zone": "America/Phoenix",
    "poi": 170.0,
    "capacity_dc": 219.98,
    "capacity_ac": 198.0,
    "capacity_bess_power_ac": 213.75,
    "capacity_bess_energy_bol_dc": 1180.8,
    "has_event_integration": True,
    "has_report_integration": True,
    "has_quality_integration": False,
    "has_block_layout": True,
    "has_pv_pcs_layout": True,
    "has_tracker_layout": True,
    "has_pv_dc_combiner_layout": True,
    "has_met_stations": True,
    "has_pv_pcs_modules": True,
    "has_pv_dc_combiners": True,
    "has_trackers": True,
    "has_bess_blocks": False,
    "has_bess_pcss": False,
    "has_bess_enclosures": False,
    "has_bess_banks": False,
    "has_bess_strings": False,
    "has_backtracking": False,
    "ppa": {"rate": 30.0, "type": "flat_rate"},
    "cod": datetime.date(2025, 3, 1),
    "spec": MockProjectSpec(
        used_device_type_ids=[
            DeviceType.GHOST,
            DeviceType.PROJECT,
            DeviceType.PV_INVERTER,
            DeviceType.PV_INVERTER_MODULE,
            DeviceType.MET_STATION,
            DeviceType.METER,
            DeviceType.PV_BLOCK,
            DeviceType.PPC,
            DeviceType.PV_DC_COMBINER,
            DeviceType.PV_MVT,
            DeviceType.PV_MV_COLLECTOR_CIRCUIT,
            DeviceType.BESS_MV_COLLECTOR_CIRCUIT,
            DeviceType.PV_MV_COLLECTOR_CIRCUIT_METER,
            DeviceType.BESS_MV_COLLECTOR_CIRCUIT_METER,
            DeviceType.PV_FEEDER,
            DeviceType.TRACKER_ZONE,
            DeviceType.TRACKER_ROW,
        ],
        used_sensor_type_ids=[
            SensorType.GHOST_UNKNOWN,
            SensorType.METER_ACTIVE_POWER,
            SensorType.PV_INVERTER_AC_POWER,
            SensorType.PV_INVERTER_MODULE_AC_POWER,
            SensorType.MET_STATION_POA,
            SensorType.MET_STATION_GHI,
            SensorType.MET_STATION_AMBIENT_TEMPERATURE,
            SensorType.MET_STATION_WIND_SPEED,
            SensorType.METER_REACTIVE_POWER,
            SensorType.PV_INVERTER_AC_POWER_SETPOINT,
            SensorType.METER_FREQUENCY,
            SensorType.METER_POWER_FACTOR,
            SensorType.METER_ENERGY_EXPORTED_TO_GRID,
            SensorType.METER_ENERGY_IMPORTED_TO_PROJECT,
            SensorType.TRACKER_ROW_POSITION,
            SensorType.TRACKER_ROW_SETPOINT,
            SensorType.PV_DC_COMBINER_CURRENT,
            SensorType.PV_INVERTER_MODULE_INTERNAL_TEMPERATURE,
            SensorType.MET_STATION_GHI_TILT,
            SensorType.MET_STATION_POA_TILT,
            SensorType.MET_STATION_RELATIVE_HUMIDITY,
            SensorType.PV_INVERTER_MODULE_DC_VOLTAGE,
            SensorType.MET_STATION_SOIL_PERCENT,
            SensorType.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER,
            SensorType.BESS_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER,
        ],
    ),
    "gsheet_id": "1XEQfggOTW8xIqK_fhBOHi5zFNK2YRmy7mr1IfeVE8vA",
    "project_type": MockProjectType(
        project_type_id=ProjectType.PVS,
        name_short="pvs",
        name_long="PV+Storage",
    ),
}


def _extract_loader_strategies(
    *, options: tuple[object, ...]
) -> set[tuple[tuple[str, str], ...]]:
    """Extract loader strategy tuples from SQLAlchemy Load options."""
    strategies: set[tuple[tuple[str, str], ...]] = set()
    for option in options:
        if not isinstance(option, Load):
            continue
        for context_item in option.context:
            if isinstance(context_item, _LoadElement):
                strategies.add(context_item.strategy)
    return strategies


def test_get_project_accepts_project_columns():
    """Ensure mapped Project columns are accepted."""
    columns = (models.Project.project_id, models.Project.name_short)
    result = get_project(project_id=TEST_PROJECT_ID, columns=columns)
    strategies = _extract_loader_strategies(options=result.query._with_options)

    assert len(result.query._with_options) == 2
    assert (("lazy", "noload"),) in strategies


def test_get_project_with_project_type_builds_projected_query():
    """Project type should be projected as a single named column."""
    columns = (models.Project.project_id,)
    joined_columns = (JOINED_PROJECT_TYPE,)

    result = get_project(
        project_id=TEST_PROJECT_ID,
        columns=columns,
        joined_columns=joined_columns,
    )
    query_sql = str(result.query)

    assert result.is_scalar is True
    assert len(result.query.column_descriptions) == 2
    assert "name_short AS project_type" in query_sql
    assert "project_type_id_1" not in query_sql


def test_get_project_with_joined_columns_defaults_to_all_project_columns():
    """Joined projections should include all project columns by default."""
    result = get_project(
        project_id=TEST_PROJECT_ID,
        joined_columns=(JOINED_PROJECT_TYPE,),
    )

    assert len(result.query.column_descriptions) == (
        len(models.Project.__table__.columns) + 1
    )


def test_get_project_with_project_type_prints_output_shapes(
    *,
    monkeypatch: pytest.MonkeyPatch,
):
    """Print the SQLAlchemy, pandas, and polars outputs for manual inspection."""
    joined_columns = (JOINED_PROJECT_TYPE,)
    db_query = get_project(
        project_id=TEST_PROJECT_ID,
        columns=(),
        joined_columns=joined_columns,
    )
    expected_output = {
        "project_type": "pvs",
    }
    compiled_queries: list[str] = []

    fake_connection = MagicMock()
    fake_connection.dialect = postgresql.dialect()
    fake_connection.get_execution_options.return_value = {}

    fake_result = MagicMock()
    fake_result.mappings.return_value.one_or_none.return_value = expected_output

    fake_executor = MagicMock()
    fake_executor.execute.return_value = fake_result
    fake_executor.connection.return_value = fake_connection

    def fake_read_sql(*args: object, **kwargs: object) -> pd.DataFrame:
        compiled_queries.append(str(args[0]))
        return pd.DataFrame([expected_output])

    def fake_read_database(*args: object, **kwargs: object) -> pl.DataFrame:
        compiled_queries.append(str(args[0]))
        return pl.DataFrame([expected_output])

    monkeypatch.setattr("core.db_query.pd.read_sql", fake_read_sql)
    monkeypatch.setattr("core.db_query.pl.read_database", fake_read_database)

    sqlalchemy_output = db_query.get(
        executor=fake_executor,
        output_type=OutputType.SQLALCHEMY,
    )
    pandas_output = db_query.get(
        executor=fake_executor,
        output_type=OutputType.PANDAS,
    )
    polars_output = db_query.get(
        executor=fake_executor,
        output_type=OutputType.POLARS,
    )

    print("sqlalchemy:", sqlalchemy_output)
    print("pandas:", pandas_output.to_dict(orient="records"))
    print("polars:", polars_output.to_dicts())

    assert sqlalchemy_output == expected_output
    assert pandas_output.to_dict(orient="records") == [expected_output]
    assert polars_output.to_dicts() == [expected_output]
    assert compiled_queries
    assert all("AS project_type" in query for query in compiled_queries)
    assert all("project_type_id_1" not in query for query in compiled_queries)


def test_get_project_found_default():
    """
    Test get_project when no explicit columns are requested.
    """
    test_id = TEST_PROJECT_ID

    result = get_project(project_id=test_id)
    strategies = _extract_loader_strategies(options=result.query._with_options)

    assert isinstance(result, DbQuery)
    assert (("lazy", "noload"),) in strategies
    criteria = result.query._where_criteria
    assert len(criteria) == 1
    assert criteria[0].right.value == test_id


def test_get_project_found_with_columns():
    """
    Test get_project when a subset of columns is requested.
    """
    test_id = TEST_PROJECT_ID
    columns = (models.Project.project_id, models.Project.name_short)

    result = get_project(project_id=test_id, columns=columns)
    strategies = _extract_loader_strategies(options=result.query._with_options)

    assert isinstance(result, DbQuery)
    assert (("lazy", "noload"),) in strategies
    criteria = result.query._where_criteria
    assert len(criteria) == 1
    assert criteria[0].right.value == test_id


def test_get_project_not_found():
    """
    Test get_project query when the project is not found.
    """
    test_id = UUID("11111111-1111-1111-1111-111111111111")

    result = get_project(project_id=test_id)
    strategies = _extract_loader_strategies(options=result.query._with_options)

    assert isinstance(result, DbQuery)
    assert (("lazy", "noload"),) in strategies
    criteria = result.query._where_criteria
    assert len(criteria) == 1
    assert criteria[0].right.value == test_id
