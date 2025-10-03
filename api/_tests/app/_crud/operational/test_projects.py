# test_crud.py
import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

# Adjust imports as needed for your project structure
from sqlalchemy.orm import Session

from core import model_list, models
from core.crud.operational.projects import get_project

# ... (Keep Mock classes, EXPECTED_PROJECT_DATA, TEST_PROJECT_ID) ...
TEST_PROJECT_ID = UUID("043fecf7-6cce-4228-acda-b1f23fd6d5f5")


# --- Mock Classes (MockPoint, MockPolygon, MockProjectSpec, MockProjectType, MockProject) ---
# (Keep these as they were defined in the previous correct version)
class MockPoint:
    def __init__(self, type, coordinates):  # skip-star-syntax
        self.type, self.coordinates = type, coordinates

    def __eq__(self, other):  # skip-star-syntax
        return (
            isinstance(other, MockPoint)
            and self.type == other.type
            and self.coordinates == other.coordinates
        )


class MockPolygon:
    def __init__(self, type, coordinates):  # skip-star-syntax
        self.type, self.coordinates = type, coordinates

    def __eq__(self, other):  # skip-star-syntax
        return (
            isinstance(other, MockPolygon)
            and self.type == other.type
            and self.coordinates == other.coordinates
        )


class MockProjectSpec:
    def __init__(self, **kwargs):  # skip-star-syntax
        self.__dict__.update(kwargs)

    def __eq__(self, other):  # skip-star-syntax
        return isinstance(other, MockProjectSpec) and self.__dict__ == other.__dict__


class MockProjectType:
    def __init__(self, **kwargs):  # skip-star-syntax
        self.__dict__.update(kwargs)

    def __eq__(self, other):  # skip-star-syntax
        return isinstance(other, MockProjectType) and self.__dict__ == other.__dict__


class MockProject:
    def __init__(self, **kwargs):  # skip-star-syntax
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __eq__(self, other):  # skip-star-syntax
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
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            9,
            15,
            16,
            17,
            19,
            20,
            23,
            28,
            29,
        ],
        used_sensor_type_ids=[
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            11,
            12,
            13,
            14,
            24,
            25,
            27,
            34,
            35,
            36,
            37,
            38,
            39,
            40,
            41,
        ],
    ),
    "gsheet_id": "1XEQfggOTW8xIqK_fhBOHi5zFNK2YRmy7mr1IfeVE8vA",
    "project_type": MockProjectType(
        project_type_id=3,
        name_short="pvs",
        name_long="PV+Storage",
    ),
}


@pytest.fixture
def mock_db_session():
    """Fixture to create a mock SQLAlchemy Session."""
    mock = MagicMock(spec=Session)
    mock_query = mock.query.return_value
    mock_options = mock_query.options.return_value
    mock_filter = mock_options.filter.return_value
    mock_filter.first = MagicMock()
    return mock


@pytest.fixture
def mock_project_instance():
    """Fixture to create a MOCK Project instance based on expected data."""
    instance = MockProject(**EXPECTED_PROJECT_DATA)
    return instance


# Adjust the path 'core.crud.operational.projects.get_project_options' if needed
@patch("core.crud.operational.projects.get_project_options")
def test_get_project_found_deep(  # skip-star-syntax
    mock_get_options,
    mock_db_session,
    mock_project_instance,
    mocker,
):
    """
    Test get_project when the project is found with deep=True.
    """
    test_id = TEST_PROJECT_ID
    deep_load = True
    mock_options_result = [mocker.MagicMock()]  # A list containing one mock
    mock_get_options.return_value = mock_options_result

    mock_db_session.query.return_value.options.return_value.filter.return_value.first.return_value = mock_project_instance

    result = get_project(db=mock_db_session, project_id=test_id, deep=deep_load).model()

    assert result == mock_project_instance
    mock_db_session.query.assert_called_once_with(models.Project)
    mock_get_options.assert_called_once_with(deep=deep_load)

    # --- MODIFIED ASSERTION ---
    # Expect options to be called with the LIST itself, not its unpacked content
    mock_db_session.query.return_value.options.assert_called_once_with(
        mock_options_result,
    )
    # ---

    mock_db_session.query.return_value.options.return_value.filter.assert_called_once()
    mock_db_session.query.return_value.options.return_value.filter.return_value.first.assert_called_once()


@patch("core.crud.operational.projects.get_project_options")
def test_get_project_found_shallow(  # skip-star-syntax
    mock_get_options,
    mock_db_session,
    mock_project_instance,
    mocker,
):
    """
    Test get_project when the project is found with deep=False.
    """
    test_id = TEST_PROJECT_ID
    deep_load = False
    mock_options_result = []  # Shallow load options (empty list)
    mock_get_options.return_value = mock_options_result

    mock_db_session.query.return_value.options.return_value.filter.return_value.first.return_value = mock_project_instance

    result = get_project(db=mock_db_session, project_id=test_id, deep=deep_load).model()

    assert result == mock_project_instance
    mock_db_session.query.assert_called_once_with(models.Project)
    mock_get_options.assert_called_once_with(deep=deep_load)

    # --- MODIFIED ASSERTION ---
    # Assuming the production code calls options([]) when the list is empty
    # If it skips the call instead, use assert_not_called()
    mock_db_session.query.return_value.options.assert_called_once_with(
        mock_options_result,  # Expect call with the empty list: options([])
    )
    # ---

    # If your production code *skips* the .options() call for an empty list, use this instead:
    # mock_db_session.query.return_value.options.assert_not_called()

    mock_db_session.query.return_value.options.return_value.filter.assert_called_once()
    mock_db_session.query.return_value.options.return_value.filter.return_value.first.assert_called_once()


@patch("core.crud.operational.projects.get_project_options")
def test_get_project_not_found(  # skip-star-syntax
    mock_get_options,
    mock_db_session,
    mocker,
):  # skip-star-syntax
    """
    Test get_project when the project is not found.
    """
    test_id = UUID("11111111-1111-1111-1111-111111111111")
    deep_load = True
    mock_options_result = [mocker.MagicMock()]  # List containing one mock
    mock_get_options.return_value = mock_options_result

    mock_db_session.query.return_value.options.return_value.filter.return_value.first.return_value = None

    with pytest.raises(model_list.UninitializedError):
        get_project(db=mock_db_session, project_id=test_id, deep=deep_load).model()
