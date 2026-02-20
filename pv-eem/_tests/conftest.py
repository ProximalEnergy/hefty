import logging
import sys
from typing import Any

import polars as pl
from _utils.logger import setup_logger
from interfaces import (
    InverterDeviceSeries,
    SystemSeries,
    TransformerDeviceSeries,
)
from p01_get_data.source_proximal.s04_get_system_data import (
    RackingControlsAlgorithm,
    System,
)

setup_logger(level=logging.INFO, environment="DEV")
logger = logging.getLogger(__name__)


# --- Mocks ---
def mock_met_data_raw(file):
    try:
        mock_df = pl.read_parquet(f"_tests/_artifacts/{file}")
    except FileNotFoundError:
        logger.info("File not found: _tests/_artifacts/%s", file)
        sys.exit(1)

    async def mock_async_met_data_raw(*args: Any, **kwargs: Any):
        logger.info("MONKEYPATCH MET DATA RAW")
        return mock_df

    return mock_async_met_data_raw


def mock_get_system_data():
    mock_df_pl = pl.DataFrame(
        {
            "string_id": [0],
            "combiner_device_id": [0],
            "module_equipment_id": [9],
            "modules_per_string": [26],
            "strings_per_combiner": [303],
            "racking_equipment_id": [2],
            "racking_controls_gcr": [0.415],
            "dc_line_to_combiner_stc": [1.5],
            "dc_line_to_inverter_stc": [0.35],
            "pcs_device_id": [179],
            "pcs_equipment_id": [0],
            "transformer_device_id": [0],
            "transformer_equipment_id": [1],
            "block_device_id": [1],
            "circuit_device_id": [1],
            "met_name": ["06"],
            "pitch": [0.0],
            "racking_controls_algorithm": [RackingControlsAlgorithm.FIXED.value],
            "racking_device_id": [-999],
        }
    )

    # Convert to pandas DataFrame as System dataclass expects pd.Series
    mock_df_pd = mock_df_pl.to_pandas()

    # Create an instance of the System dataclass
    mock_system_instance = System(
        string_id=SystemSeries(mock_df_pd.loc[:, "string_id"]),
        module_equipment_id=SystemSeries(mock_df_pd.loc[:, "module_equipment_id"]),
        modules_per_string=SystemSeries(mock_df_pd.loc[:, "modules_per_string"]),
        strings_per_combiner=SystemSeries(mock_df_pd.loc[:, "strings_per_combiner"]),
        dc_line_to_combiner_stc=SystemSeries(
            mock_df_pd.loc[:, "dc_line_to_combiner_stc"]
        ),
        combiner_device_id=SystemSeries(mock_df_pd.loc[:, "combiner_device_id"]),
        pitch=SystemSeries(mock_df_pd.loc[:, "pitch"]),
        racking_controls_gcr=SystemSeries(mock_df_pd.loc[:, "racking_controls_gcr"]),
        racking_equipment_id=SystemSeries(mock_df_pd.loc[:, "racking_equipment_id"]),
        racking_controls_algorithm=SystemSeries(
            mock_df_pd.loc[:, "racking_controls_algorithm"]
        ),
        racking_device_id=SystemSeries(mock_df_pd.loc[:, "racking_device_id"]),
        dc_line_to_inverter_stc=SystemSeries(
            mock_df_pd.loc[:, "dc_line_to_inverter_stc"]
        ),
        pcs_equipment_id=InverterDeviceSeries(mock_df_pd.loc[:, "pcs_equipment_id"]),
        pcs_device_id=InverterDeviceSeries(mock_df_pd.loc[:, "pcs_device_id"]),
        transformer_equipment_id=TransformerDeviceSeries(
            mock_df_pd.loc[:, "transformer_equipment_id"]
        ),
        transformer_device_id=TransformerDeviceSeries(
            mock_df_pd.loc[:, "transformer_device_id"]
        ),
        block_device_id=SystemSeries(mock_df_pd.loc[:, "block_device_id"]),
        circuit_device_id=SystemSeries(mock_df_pd.loc[:, "circuit_device_id"]),
        met_name=SystemSeries(mock_df_pd.loc[:, "met_name"]),
    )

    # Create an async mock function that returns the System instance
    async def mock_async_get_system_data(*args: Any, **kwargs: Any):
        logger.info("MONKEYPATCH GET SYSTEM DATA")
        return mock_system_instance

    return mock_async_get_system_data


def mock_calc_if_backtracking(system, modules):
    """Intercept the system DataFrame after it's created and modify it."""
    system["racking_controls_algorithm"] = False  # Modify the system DataFrame
    return system
