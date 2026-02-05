# test_crud.py
import datetime
from unittest.mock import patch
from uuid import UUID

from core.crud.operational.projects import get_project
from core.db_query import DbQuery
from core.enumerations import DeviceType, ProjectType, SensorType
from sqlalchemy.orm import noload, selectinload

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
            DeviceType.PV_PCS,
            DeviceType.PV_PCS_MODULE,
            DeviceType.MET_STATION,
            DeviceType.METER,
            DeviceType.PV_BLOCK,
            DeviceType.PPC,
            DeviceType.PV_DC_COMBINER,
            DeviceType.PV_MVT,
            DeviceType.PV_MV_CIRCUIT,
            DeviceType.BESS_MV_CIRCUIT,
            DeviceType.PV_MV_CIRCUIT_METER,
            DeviceType.BESS_MV_CIRCUIT_METER,
            DeviceType.PV_CIRCUIT,
            DeviceType.TRACKER_ZONE,
            DeviceType.TRACKER_ROW,
        ],
        used_sensor_type_ids=[
            SensorType.GHOST_UNKNOWN,
            SensorType.METER_ACTIVE_POWER,
            SensorType.PV_PCS_AC_POWER,
            SensorType.PV_PCS_MODULE_AC_POWER,
            SensorType.MET_STATION_POA,
            SensorType.MET_STATION_GHI,
            SensorType.MET_STATION_AMBIENT_TEMPERATURE,
            SensorType.MET_STATION_WIND_SPEED,
            SensorType.METER_REACTIVE_POWER,
            SensorType.PV_PCS_AC_POWER_SETPOINT,
            SensorType.METER_FREQUENCY,
            SensorType.METER_POWER_FACTOR,
            SensorType.METER_DELIVERED_ENERGY,
            SensorType.METER_CONSUMED_ENERGY,
            SensorType.TRACKER_POSITION,
            SensorType.TRACKER_SETPOINT,
            SensorType.PV_DC_COMBINER_CURRENT,
            SensorType.PV_PCS_MODULE_INTERNAL_TEMPERATURE,
            SensorType.MET_STATION_GHI_TILT,
            SensorType.MET_STATION_POA_TILT,
            SensorType.MET_STATION_RELATIVE_HUMIDITY,
            SensorType.PV_PCS_MODULE_DC_VOLTAGE,
            SensorType.MET_STATION_SOIL_PERCENT,
            SensorType.PV_MV_CIRCUIT_METER_ACTIVE_POWER,
            SensorType.BESS_MV_CIRCUIT_METER_ACTIVE_POWER,
        ],
    ),
    "gsheet_id": "1XEQfggOTW8xIqK_fhBOHi5zFNK2YRmy7mr1IfeVE8vA",
    "project_type": MockProjectType(
        project_type_id=ProjectType.PVS,
        name_short="pvs",
        name_long="PV+Storage",
    ),
}


# Adjust the path 'core.crud.operational.projects.get_project_options' if needed
@patch("core.crud.operational.projects.get_project_options")
def test_get_project_found_deep(  # nosemgrep: python-enforce-keyword-only-args
    mock_get_options,
    mocker,
):
    """
    Test get_project when the project is found with deep=True.
    """
    test_id = TEST_PROJECT_ID
    deep_load = True
    mock_option = selectinload(models.Project.project_type)
    mock_get_options.return_value = mock_option

    result = get_project(project_id=test_id, deep=deep_load)

    assert isinstance(result, DbQuery)
    mock_get_options.assert_called_once_with(deep=deep_load)
    assert mock_option in result.query._with_options
    criteria = result.query._where_criteria
    assert len(criteria) == 1
    assert criteria[0].right.value == test_id


@patch("core.crud.operational.projects.get_project_options")
def test_get_project_found_shallow(  # nosemgrep: python-enforce-keyword-only-args
    mock_get_options,
    mocker,
):
    """
    Test get_project when the project is found with deep=False.
    """
    test_id = TEST_PROJECT_ID
    deep_load = False
    mock_option = noload(models.Project.project_type)
    mock_get_options.return_value = mock_option

    result = get_project(project_id=test_id, deep=deep_load)

    assert isinstance(result, DbQuery)
    mock_get_options.assert_called_once_with(deep=deep_load)
    assert mock_option in result.query._with_options
    criteria = result.query._where_criteria
    assert len(criteria) == 1
    assert criteria[0].right.value == test_id


@patch("core.crud.operational.projects.get_project_options")
def test_get_project_not_found(  # nosemgrep: python-enforce-keyword-only-args
    mock_get_options,
    mocker,
):
    """
    Test get_project query when the project is not found.
    """
    test_id = UUID("11111111-1111-1111-1111-111111111111")
    deep_load = True
    mock_option = selectinload(models.Project.project_type)
    mock_get_options.return_value = mock_option

    result = get_project(project_id=test_id, deep=deep_load)

    assert isinstance(result, DbQuery)
    mock_get_options.assert_called_once_with(deep=deep_load)
    assert mock_option in result.query._with_options
    criteria = result.query._where_criteria
    assert len(criteria) == 1
    assert criteria[0].right.value == test_id
