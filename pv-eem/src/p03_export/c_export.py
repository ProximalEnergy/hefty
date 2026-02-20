from typing import Any

import pandas as pd
import sqlalchemy
from interfaces import CombinerTimeSeries, InverterTimeSeries, TransformerTimeSeries
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance
from p02_simulation.p4_dc_iv._utils.combine_tier_codes import combine_tier_codes
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner
from p02_simulation.p5_inverter.c_inverter import InverterPower
from p02_simulation.p6_transformer.c_transformer import TransformerPower
from p02_simulation.p8_poi.c_poi import ProjectPower
from p03_export.s00_simulation_level import SimulationLevel
from p03_export.s01_to_proximal_db import upload_to_proximal_db
from p03_export.s02_to_file import export_to_file


def export_simulation_results(
    *,
    results: PlaneOfArrayIrradiance
    | PowerAtCombiner
    | InverterPower
    | TransformerPower
    | ProjectPower,
    project_name_short: str,
    simulation_start: str | None,
    simulation_config: SimulationConfig,
    engine: sqlalchemy.engine.Engine,
    version: str,
    ENVIRONMENT: str,
):
    """Export simulation results to Proximal DB"""
    # --- Create results dataframe ---
    concat_columns: list[Any] = [results.time, results.tier, results.tier_codes]

    if type(results) == PlaneOfArrayIrradiance:
        simulation_level = SimulationLevel.PLANE_OF_ARRAY_IRRADIANCE
        concat_columns.extend([results.gpoai, results.device_ids])
        df_temp = pd.concat(concat_columns, axis=1)
        agg_dict = {
            "gpoai": "mean",  # average gpoai
            "time": "first",  # first time
            "tier": "max",  # highest tier
            "tier_codes": combine_tier_codes,  # combine unique tier codes
        }
        df = df_temp.groupby("device_id").agg(agg_dict).reset_index()
    elif type(results) == PowerAtCombiner:
        simulation_level = SimulationLevel.COMBINER
        results.device_ids = CombinerTimeSeries(results.device_ids.rename("device_id"))
        concat_columns.extend([results.p_mp, results.device_ids])
        df = pd.concat(concat_columns, axis=1)
    elif type(results) == InverterPower:
        simulation_level = SimulationLevel.INVERTER
        results.device_ids = InverterTimeSeries(results.device_ids.rename("device_id"))
        concat_columns.extend([results.power, results.device_ids])
        df = pd.concat(concat_columns, axis=1)
    elif type(results) == TransformerPower:
        simulation_level = SimulationLevel.TRANSFORMER
        results.device_ids = TransformerTimeSeries(
            results.device_ids.rename("device_id")
        )
        concat_columns.extend([results.power, results.device_ids])
        df = pd.concat(concat_columns, axis=1)
    elif type(results) == ProjectPower:
        simulation_level = SimulationLevel.INTERCONNECTION
        # Create a Series of zeros with the same index as the power data
        device_ids_series = pd.Series(1, index=results.power.index, name="device_id")
        concat_columns.extend([results.power, device_ids_series])
        df = pd.concat(concat_columns, axis=1)
    else:
        raise ValueError(
            "Simulation must be PlaneOfArrayIrradiance,"
            "PowerAtCombiner, PowerAtInverter, TransformerPower, or ProjectPower"
        )

    match ENVIRONMENT:
        # --- PROD ---
        # Upload to Proximal DB
        case "PROD" | "STAGE":
            upload_to_proximal_db(
                results=df,
                project_name_short=project_name_short,
                simulation_level=simulation_level,
                simulation_config=simulation_config,
                version=version,
                engine=engine,
            )

        # --- DEV ---
        # Plot via Plotly
        # Export to Parquet
        case "DEV" | "VALIDATE":
            export_to_file(
                results=df,
                simulation_level=simulation_level,
                project_name_short=project_name_short,
                simulation_start=simulation_start,
                ENVIRONMENT=ENVIRONMENT,
            )

        case _:
            raise ValueError(
                f"ENVIRONMENT {ENVIRONMENT} not supportedmust be 'prod' or 'dev'"
            )
