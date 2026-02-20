import asyncio
import logging
import os

import polars as pl
from main import get_expected_energy
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import (
    ModelDCWiringToCombiner,
)
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import ModelDCWiringToInverter

from _tests.conftest import mock_met_data_raw

# --- Config ---
pl.Config.set_tbl_cols(-1)
pl.Config.set_tbl_rows(-1)
logger = logging.getLogger(__name__)


def test_zero_output(monkeypatch):
    """Tests to make sure that given a set of inputs, the outputs
    do not contain zeros
    """
    # --- Constants ---
    os.environ["ENVIRONMENT"] = "DEV"
    MET_DATA_RAW = [
        "sun_streams_4/2025_08_05/met_data_raw_05:50:00.pq",
    ]

    for met_data_raw_file in MET_DATA_RAW:
        logger.info("%s", met_data_raw_file)
        # --- File Load ---
        monkeypatch.setattr(
            "p01_get_data.source_proximal.s04_get_met_data.get_met_data",
            mock_met_data_raw(file=met_data_raw_file),
        )

        # --- Main Simulation ---
        _results: dict = asyncio.run(
            get_expected_energy(
                # ARGS
                project_name_short="serrano",
                simulation_temporal_mode=SimulationTemporalMode.WINDOW,
                simulation_start="2025-04-24 19:25:00",
                simulation_end="2025-04-24 19:30:00",
                # KWARGS
                sun_position_offset=0,
                degradation=ModelDegradation.NONE,
                soiling=ModelSoiling.NONE,
                circumsolar=ModelCircumsolar.DIFFUSE,
                dc_wiring_to_combiner=ModelDCWiringToCombiner.TARGET_STC,
                dc_wiring_to_inverter=ModelDCWiringToInverter.TARGET_STC,
            )
        )

        # Get the script's absolute directory
        cwd = os.getcwd()

        # --- Combiners ---
        combiners = pl.read_parquet(f"{cwd}/_tests/_artifacts/_combiner.pq")
        filtered_combiners = combiners.filter(pl.col("p_mp") < 1)
        assert len(filtered_combiners) < 1
