import asyncio
import logging
import os
from pathlib import Path

import polars as pl
from main import get_expected_energy
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import (
    ModelDCWiringToCombiner,
)
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import (
    ModelDCWiringToInverter,
)
from p03_export.s00_simulation_level import SimulationLevel

from _tests.snapshot_test_helpers import (
    build_output_file_path,
    install_snapshot_inputs_loader_patch,
    install_unique_export_patch,
    remove_output_files_if_exist,
)

# --- Config ---
pl.Config.set_tbl_cols(-1)
pl.Config.set_tbl_rows(-1)
logger = logging.getLogger(__name__)

SNAPSHOT_NAME = Path(__file__).stem
TEST_NAME = "test_changed_module_zero_output"
OUTPUT_NAMESPACE = f"{SNAPSHOT_NAME}_{TEST_NAME}"
PROJECT_NAME_SHORT = "double_black_diamond"
SIMULATION_LEVELS = [
    SimulationLevel.COMBINER,
    SimulationLevel.INVERTER,
    SimulationLevel.INTERCONNECTION,
]
STATIC_OUTPUT_ROOT = (
    Path(__file__).resolve().parents[1] / "_artifacts" / "sigurd" / "2025_08_18"
)
STATIC_OUTPUT_FILES = {
    SimulationLevel.COMBINER: STATIC_OUTPUT_ROOT / "_combiner.pq",
    SimulationLevel.INVERTER: STATIC_OUTPUT_ROOT / "_inverter.pq",
    SimulationLevel.INTERCONNECTION: STATIC_OUTPUT_ROOT / "_interconnection.pq",
}
SIMULATION_CASES = [
    {
        "artifact": "double_black_diamond/2025_04_24/met_data_raw.pq",
        "simulation_start": "2025-04-24 19:25:00",
        "simulation_end": "2025-04-24 19:30:00",
    },
    {
        "artifact": "double_black_diamond/2025_05_01/met_data_raw.pq",
        "simulation_start": "2025-05-01 19:25:00",
        "simulation_end": "2025-05-01 19:30:00",
    },
]


def test_changed_module_zero_output(monkeypatch):
    """Tests to make sure that given a set of inputs, the outputs
    do not contain zeros
    """
    os.environ["ENVIRONMENT"] = "DEV"
    install_snapshot_inputs_loader_patch(
        monkeypatch=monkeypatch,
        snapshot_name=SNAPSHOT_NAME,
    )
    install_unique_export_patch(
        monkeypatch=monkeypatch,
        test_namespace=OUTPUT_NAMESPACE,
        static_output_files=STATIC_OUTPUT_FILES,
    )

    for simulation_case in SIMULATION_CASES:
        logger.info("%s", simulation_case["artifact"])
        simulation_start = simulation_case["simulation_start"]
        simulation_end = simulation_case["simulation_end"]

        remove_output_files_if_exist(
            test_namespace=OUTPUT_NAMESPACE,
            project_name_short=PROJECT_NAME_SHORT,
            simulation_start=simulation_start,
            simulation_levels=SIMULATION_LEVELS,
        )

        # --- Main Simulation ---
        results: dict = asyncio.run(
            get_expected_energy(
                # ARGS
                project_name_short=PROJECT_NAME_SHORT,
                simulation_temporal_mode=SimulationTemporalMode.WINDOW,
                simulation_start=simulation_start,
                simulation_end=simulation_end,
                # KWARGS
                sun_position_offset=0,
                degradation=ModelDegradation.NONE,
                soiling=ModelSoiling.NONE,
                circumsolar=ModelCircumsolar.DIFFUSE,
                dc_wiring_to_combiner=ModelDCWiringToCombiner.TARGET_STC,
                dc_wiring_to_inverter=ModelDCWiringToInverter.TARGET_STC,
            )
        )
        assert results.get("status_code") == 200, results

        # --- Combiners ---
        combiners = pl.read_parquet(
            build_output_file_path(
                test_namespace=OUTPUT_NAMESPACE,
                project_name_short=PROJECT_NAME_SHORT,
                simulation_start=simulation_start,
                simulation_level=SimulationLevel.COMBINER,
            )
        )
        filtered_combiners = combiners.filter(pl.col("p_mp") < 1)
        assert len(filtered_combiners) < 1

        # --- Inverters ---
        inverters = pl.read_parquet(
            build_output_file_path(
                test_namespace=OUTPUT_NAMESPACE,
                project_name_short=PROJECT_NAME_SHORT,
                simulation_start=simulation_start,
                simulation_level=SimulationLevel.INVERTER,
            )
        )
        filtered_inverters = inverters.filter(pl.col("p_mp") < 1)
        assert len(filtered_inverters) < 1

        # --- POI ---
        poi = pl.read_parquet(
            build_output_file_path(
                test_namespace=OUTPUT_NAMESPACE,
                project_name_short=PROJECT_NAME_SHORT,
                simulation_start=simulation_start,
                simulation_level=SimulationLevel.INTERCONNECTION,
            )
        )
        filtered_poi = poi.filter(pl.col("p_mp") < 1)
        assert len(filtered_poi) < 1
