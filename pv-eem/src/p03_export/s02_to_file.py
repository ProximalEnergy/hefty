import logging
import os

import pandas as pd
from p03_export.s00_simulation_level import SimulationLevel

logger = logging.getLogger(__name__)


def export_to_file(
    *,
    results: pd.DataFrame,
    simulation_level: SimulationLevel,
    project_name_short: str,
    simulation_start: str | None,
    ENVIRONMENT: str,
):
    """Export simulation results"""
    # --- EXPORT ---
    match ENVIRONMENT:
        case "DEV":
            results.to_parquet(
                f"_tests/_artifacts/_{simulation_level}.pq",
                index=False,
            )
        case "VALIDATE":
            # Create directory if it doesn't exist
            if simulation_start:
                output_dir = (
                    f"_tests/_artifacts/"
                    f"{project_name_short}/{simulation_start[:10].replace('-', '_')}/"
                )
            else:
                output_dir = f"_tests/_artifacts/{project_name_short}"
            os.makedirs(output_dir, exist_ok=True)

            results.to_parquet(
                f"{output_dir}/_{simulation_level}.pq",
                index=False,
            )

    logger.info("... Export to Parquet Complete")
