import os
import sys
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import sqlalchemy

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from interfaces import (
    CombinerTimeSeries,
    InverterTimeSeries,
    TimeSeries,
    TransformerTimeSeries,
)
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner
from p02_simulation.p5_inverter.c_inverter import InverterPower
from p02_simulation.p6_transformer.c_transformer import TransformerPower
from p02_simulation.p8_poi.c_poi import ProjectPower
from p03_export.c_export import export_simulation_results
from p03_export.s00_simulation_level import SimulationLevel


def create_project_power_instance(*, time, power, tier, tier_codes):
    """Create a ProjectPower instance by directly setting attributes."""
    instance = object.__new__(ProjectPower)
    instance.time = time
    instance.power = power
    instance.tier = tier
    instance.tier_codes = tier_codes
    return instance


def create_plane_of_array_irradiance_instance(
    *, time, tier, tier_codes, gpoai, device_ids
):
    """Create a PlaneOfArrayIrradiance instance by directly setting attributes."""
    instance = object.__new__(PlaneOfArrayIrradiance)
    instance.time = time
    instance.tier = tier
    instance.tier_codes = tier_codes
    instance.gpoai = gpoai
    instance.device_ids = device_ids
    return instance


def create_power_at_combiner_instance(*, time, tier, tier_codes, p_mp, device_ids):
    """Create a PowerAtCombiner instance by directly setting attributes."""
    instance = object.__new__(PowerAtCombiner)
    instance.time = time
    instance.tier = tier
    instance.tier_codes = tier_codes
    instance.p_mp = p_mp
    instance.device_ids = device_ids
    return instance


def create_inverter_power_instance(*, time, tier, tier_codes, power, device_ids):
    """Create an InverterPower instance by directly setting attributes."""
    instance = object.__new__(InverterPower)
    instance.time = time
    instance.tier = tier
    instance.tier_codes = tier_codes
    instance.power = power
    instance.device_ids = device_ids
    return instance


def create_transformer_power_instance(*, time, tier, tier_codes, power, device_ids):
    """Create a TransformerPower instance by directly setting attributes."""
    instance = object.__new__(TransformerPower)
    instance.time = time
    instance.tier = tier
    instance.tier_codes = tier_codes
    instance.power = power
    instance.device_ids = device_ids
    return instance


class TestExportSimulationResults(unittest.TestCase):
    """TestExportSimulationResults."""

    def setUp(self):  # skip-star-syntax
        """Set up test fixtures before each test method."""
        # Create sample time index
        self.time_index = pd.date_range("2023-01-01", periods=5, freq="h")
        self.time_series = TimeSeries(self.time_index, name="time")

        # Create sample tier and tier_codes with proper index
        self.tier_series = TimeSeries(
            [1, 1, 2, 2, 1], index=self.time_index, name="tier"
        )
        self.tier_codes_series = TimeSeries(
            ["A", "A", "B", "B", "A"], index=self.time_index, name="tier_codes"
        )

        # Create sample power data with proper index
        self.power_data = TimeSeries(
            [100.5, 150.2, 200.8, 175.3, 125.7], index=self.time_index, name="power"
        )

        # Mock simulation config
        self.simulation_config = Mock(spec=SimulationConfig)

        # Mock engine
        self.engine = Mock(spec=sqlalchemy.engine.Engine)

        # Test parameters
        self.project_name_short = "test_project"
        self.version = "1.0.0"

    def create_mock_project_power(self):  # skip-star-syntax
        """Create a mock ProjectPower object."""
        return create_project_power_instance(
            time=self.time_series,
            power=self.power_data,
            tier=self.tier_series,
            tier_codes=self.tier_codes_series,
        )

    def create_mock_plane_of_array_irradiance(self):  # skip-star-syntax
        """Create a mock PlaneOfArrayIrradiance object."""
        return create_plane_of_array_irradiance_instance(
            time=self.time_series,
            tier=self.tier_series,
            tier_codes=self.tier_codes_series,
            gpoai=TimeSeries(
                [800, 850, 900, 875, 825], index=self.time_index, name="gpoai"
            ),
            device_ids=TimeSeries(
                [1, 2, 3, 4, 5], index=self.time_index, name="device_id"
            ),
        )

    def create_mock_power_at_combiner(self):  # skip-star-syntax
        """Create a mock PowerAtCombiner object."""
        return create_power_at_combiner_instance(
            time=self.time_series,
            tier=self.tier_series,
            tier_codes=self.tier_codes_series,
            p_mp=self.power_data,
            device_ids=TimeSeries(
                [10, 11, 12, 13, 14], index=self.time_index, name="device_id"
            ),
        )

    def create_mock_inverter_power(self):  # skip-star-syntax
        """Create a mock InverterPower object."""
        return create_inverter_power_instance(
            time=self.time_series,
            tier=self.tier_series,
            tier_codes=self.tier_codes_series,
            power=self.power_data,
            device_ids=TimeSeries(
                [20, 21, 22, 23, 24], index=self.time_index, name="device_id"
            ),
        )

    def create_mock_transformer_power(self):  # skip-star-syntax
        """Create a mock TransformerPower object."""
        return create_transformer_power_instance(
            time=self.time_series,
            tier=self.tier_series,
            tier_codes=self.tier_codes_series,
            power=self.power_data,
            device_ids=TimeSeries(
                [30, 31, 32, 33, 34], index=self.time_index, name="device_id"
            ),
        )

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_project_power_device_ids_series_set_to_1_prod(self, mock_upload):
        """Test device_ids_series is set to 1 for ProjectPower in PROD env."""
        project_power = self.create_mock_project_power()

        export_simulation_results(
            results=project_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="PROD",
        )

        # Verify upload_to_proximal_db was called
        self.assertTrue(mock_upload.called)

        # Get the results dataframe that was passed to upload_to_proximal_db
        call_args = mock_upload.call_args
        results_df = call_args[1]["results"]  # Using keyword arguments

        # Filter to only rows where device_id is not NaN (the actual data rows)
        results_df_clean = results_df[results_df["device_id"].notna()]

        # Verify that device_id column exists and all values are 1
        self.assertIn("device_id", results_df_clean.columns)
        self.assertTrue((results_df_clean["device_id"] == 1).all())
        self.assertEqual(len(results_df_clean), 5)  # Should have 5 rows

        # Verify the simulation level is INTERCONNECTION
        simulation_level = call_args[1]["simulation_level"]
        self.assertEqual(simulation_level, SimulationLevel.INTERCONNECTION)

    @patch("p03_export.c_export.export_to_file")
    def test_project_power_device_ids_series_set_to_1_dev(
        self,
        mock_export_file,
    ):
        """Test device_ids_series is set to 1 for ProjectPower in DEV env."""
        project_power = self.create_mock_project_power()

        export_simulation_results(
            results=project_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="DEV",
        )

        # Verify export_to_file was called
        self.assertTrue(mock_export_file.called)

        # Get the results dataframe that was passed to export_to_file
        call_args = mock_export_file.call_args
        results_df = call_args[1]["results"]  # Using keyword arguments

        # Filter to only rows where device_id is not NaN (the actual data rows)
        results_df_clean = results_df[results_df["device_id"].notna()]

        # Verify that device_id column exists and all values are 1
        self.assertIn("device_id", results_df_clean.columns)
        self.assertTrue((results_df_clean["device_id"] == 1).all())
        self.assertEqual(len(results_df_clean), 5)  # Should have 5 rows

        # Verify the simulation level is INTERCONNECTION
        simulation_level = call_args[1]["simulation_level"]
        self.assertEqual(simulation_level, SimulationLevel.INTERCONNECTION)

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_project_power_dataframe_structure(self, mock_upload):
        """Test that the dataframe has the correct structure for ProjectPower."""
        project_power = self.create_mock_project_power()

        export_simulation_results(
            results=project_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="PROD",
        )

        # Get the results dataframe
        call_args = mock_upload.call_args
        results_df = call_args[1]["results"]

        # Filter to only rows where device_id is not NaN (the actual data rows)
        results_df_clean = results_df[results_df["device_id"].notna()]

        # Verify dataframe structure
        expected_columns = ["time", "tier", "tier_codes", "power", "device_id"]
        for col in expected_columns:
            self.assertIn(col, results_df_clean.columns)

        # Verify data integrity
        self.assertEqual(len(results_df_clean), 5)  # Should have 5 rows
        # Check if filtered rows have datetime index or time column has datetime values
        has_datetime_index = pd.api.types.is_datetime64_any_dtype(
            results_df_clean.index
        )
        has_datetime_time_col = pd.api.types.is_datetime64_any_dtype(
            results_df_clean["time"]
        )
        self.assertTrue(has_datetime_index or has_datetime_time_col)

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_combiner_power_device_ids_handling(self, mock_upload):
        """Test that device_ids are handled correctly for PowerAtCombiner."""
        combiner_power = self.create_mock_power_at_combiner()

        export_simulation_results(
            results=combiner_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="PROD",
        )

        # Verify device_ids was converted to CombinerTimeSeries and renamed
        self.assertTrue(isinstance(combiner_power.device_ids, CombinerTimeSeries))
        self.assertEqual(combiner_power.device_ids.name, "device_id")

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_inverter_power_device_ids_handling(self, mock_upload):
        """Test that device_ids are handled correctly for InverterPower."""
        inverter_power = self.create_mock_inverter_power()

        export_simulation_results(
            results=inverter_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="PROD",
        )

        # Verify device_ids was converted to InverterTimeSeries and renamed
        self.assertTrue(isinstance(inverter_power.device_ids, InverterTimeSeries))
        self.assertEqual(inverter_power.device_ids.name, "device_id")

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_transformer_power_device_ids_handling(self, mock_upload):
        """Test that device_ids are handled correctly for TransformerPower."""
        transformer_power = self.create_mock_transformer_power()

        export_simulation_results(
            results=transformer_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="PROD",
        )

        # Verify device_ids was converted to TransformerTimeSeries and renamed
        self.assertTrue(isinstance(transformer_power.device_ids, TransformerTimeSeries))
        self.assertEqual(transformer_power.device_ids.name, "device_id")

    def test_unsupported_environment_raises_error(self):  # skip-star-syntax
        """Test that unsupported ENVIRONMENT raises ValueError."""
        project_power = self.create_mock_project_power()

        with self.assertRaises(ValueError) as context:
            export_simulation_results(
                results=project_power,
                project_name_short=self.project_name_short,
                simulation_start="2023-01-01",
                simulation_config=self.simulation_config,
                engine=self.engine,
                version=self.version,
                ENVIRONMENT="INVALID",
            )

        self.assertIn("ENVIRONMENT INVALID not supported", str(context.exception))

    def test_unsupported_results_type_raises_error(self):  # skip-star-syntax
        """Test that unsupported results type raises ValueError."""
        # Create a mock object that doesn't match any expected type
        invalid_results = Mock()
        invalid_results.time = self.time_series
        invalid_results.tier = self.tier_series
        invalid_results.tier_codes = self.tier_codes_series

        with self.assertRaises(ValueError) as context:
            export_simulation_results(
                results=invalid_results,
                project_name_short=self.project_name_short,
                simulation_start="2024-08-08 00:00:00",
                simulation_config=self.simulation_config,
                engine=self.engine,
                version=self.version,
                ENVIRONMENT="DEV",
            )

        self.assertIn(
            "Simulation must be PlaneOfArrayIrradiance", str(context.exception)
        )

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_stage_environment_uses_upload_to_proximal_db(self, mock_upload):
        """Test that STAGE environment uses upload_to_proximal_db like PROD."""
        project_power = self.create_mock_project_power()

        export_simulation_results(
            results=project_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="STAGE",
        )

        # Verify upload_to_proximal_db was called for STAGE environment
        self.assertTrue(mock_upload.called)

    @patch("p03_export.c_export.upload_to_proximal_db")
    def test_project_power_device_ids_series_specifically_set_to_1(self, mock_upload):
        """Test to verify device_ids_series is created with value 1 for ProjectPower."""
        project_power = self.create_mock_project_power()

        # Verify that the power data has the expected index
        self.assertEqual(len(project_power.power.index), 5)

        export_simulation_results(
            results=project_power,
            project_name_short=self.project_name_short,
            simulation_start="2023-01-01",
            simulation_config=self.simulation_config,
            engine=self.engine,
            version=self.version,
            ENVIRONMENT="PROD",
        )

        # Get the results dataframe passed to upload_to_proximal_db
        call_args = mock_upload.call_args
        results_df = call_args[1]["results"]

        # Filter to rows with valid device_id values
        valid_rows = results_df[results_df["device_id"].notna()]

        # Test the core requirement: device_ids_series is set to 1
        device_id_values = valid_rows["device_id"].unique()
        self.assertEqual(
            len(device_id_values),
            1,
            "device_ids_series should contain only one unique value",
        )
        self.assertEqual(device_id_values[0], 1, "device_ids_series should be set to 1")

        # Verify that all device_id values are exactly 1
        all_ones = (valid_rows["device_id"] == 1).all()
        self.assertTrue(all_ones, "All device_id values must be exactly 1")

        # Verify the count matches the original power data length
        self.assertEqual(len(valid_rows), 5, "Should have 5 rows with device_id = 1")


if __name__ == "__main__":
    unittest.main()
