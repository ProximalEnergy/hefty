import logging
import random
import string

import pandas as pd
import sqlalchemy
from core.enumerations import ExpectedMetricIdEnum
from p01_get_data.s00_get_simulation_config import SimulationConfig
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation
from p03_export.s00_simulation_level import SimulationLevel
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert


def _generate_temp_table_name() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return f"temp_data_expected_{suffix}"


def upload_to_proximal_db(
    *,
    results: pd.DataFrame,
    simulation_level: SimulationLevel,
    project_name_short: str,
    simulation_config: SimulationConfig,
    engine: sqlalchemy.engine.Engine,
    version: str,
):
    # --- Determine expected_metric_id from simulation level and config ---
    """Run upload_to_proximal_db."""
    has_soiling = simulation_config.soiling == ModelSoiling.MEASURED
    has_degradation = simulation_config.degradation == ModelDegradation.WARRANTED

    match (simulation_level, has_soiling, has_degradation):
        # PV DC Combiner Power (COMBINER)
        case (SimulationLevel.COMBINER, False, False):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_DC_COMBINER_POWER_BASE.value
        case (SimulationLevel.COMBINER, True, False):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_DC_COMBINER_POWER_SOILING.value
        case (SimulationLevel.COMBINER, False, True):
            value_column_name = "p_mp"
            expected_metric_id = (
                ExpectedMetricIdEnum.PV_DC_COMBINER_POWER_DEGRADATION.value
            )
        case (SimulationLevel.COMBINER, True, True):
            value_column_name = "p_mp"
            expected_metric_id = (
                ExpectedMetricIdEnum.PV_DC_COMBINER_POWER_SOILING_DEGRADATION.value
            )

        # PV Inverter Power (INVERTER)
        case (SimulationLevel.INVERTER, False, False):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_PCS_POWER_BASE.value
        case (SimulationLevel.INVERTER, True, False):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_PCS_POWER_SOILING.value
        case (SimulationLevel.INVERTER, False, True):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_PCS_POWER_DEGRADATION.value
        case (SimulationLevel.INVERTER, True, True):
            value_column_name = "p_mp"
            expected_metric_id = (
                ExpectedMetricIdEnum.PV_PCS_POWER_SOILING_DEGRADATION.value
            )

        # PV POI Power (INTERCONNECTION)
        case (SimulationLevel.INTERCONNECTION, False, False):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_POI_POWER_BASE.value
        case (SimulationLevel.INTERCONNECTION, True, False):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_POI_POWER_SOILING.value
        case (SimulationLevel.INTERCONNECTION, False, True):
            value_column_name = "p_mp"
            expected_metric_id = ExpectedMetricIdEnum.PV_POI_POWER_DEGRADATION.value
        case (SimulationLevel.INTERCONNECTION, True, True):
            value_column_name = "p_mp"
            expected_metric_id = (
                ExpectedMetricIdEnum.PV_POI_POWER_SOILING_DEGRADATION.value
            )

        # PV DC Combiner (PLANE_OF_ARRAY_IRRADIANCE)
        case (SimulationLevel.PLANE_OF_ARRAY_IRRADIANCE, _, _):
            value_column_name = "gpoai"
            expected_metric_id = ExpectedMetricIdEnum.PV_DC_COMBINER_POAI_BASE.value

        case _:
            raise ValueError(
                f"Unsupported combination: simulation_level={simulation_level}, "
                f"soiling={simulation_config.soiling}, "
                f"degradation={simulation_config.degradation}"
            )

    # --- Convert to UTC ---
    logging.info("--- Export ---")
    logging.info(results.head())
    results = results.copy()
    results["time"] = results["time"].dt.tz_convert("UTC")

    # --- Rename columns ---
    # Rename columns to match database
    df = results[["time", value_column_name, "device_id", "tier", "tier_codes"]].copy()

    df = df.rename(
        columns={
            value_column_name: "value",
            "tier": "confidence_tier",
            "tier_codes": "confidence_codes",
        }
    )

    # --- Drop rows with NaN Values ---
    df = df.dropna(axis=0)

    # --- Clamp negative values to 0 for all levels ---
    df["value"] = df["value"].clip(lower=0)

    # --- Don't upload if empty ---
    if df.empty:
        logging.info("No data to export")
    else:
        # --- Mappings for version ---
        df["expected_metric_id"] = expected_metric_id
        df["version"] = version

        # --- SQL ---
        with engine.connect() as conn:
            # Unique name prevents collisions when parallel Lambda invocations
            # share a session via a connection pooler (e.g. RDS Proxy).
            # TEMP TABLE auto-drops on session close; we also drop explicitly
            # after the upsert so the name is freed within long-lived sessions.
            temp_table = _generate_temp_table_name()
            conn.execute(
                text(
                    f"CREATE TEMP TABLE {temp_table} "
                    f"(LIKE {project_name_short}.data_expected INCLUDING DEFAULTS)"
                )
            )

            df.to_sql(
                temp_table,
                con=conn,
                if_exists="append",
                index=False,
            )

            metadata = sqlalchemy.MetaData()
            target_table = sqlalchemy.Table(
                "data_expected",
                metadata,
                schema=project_name_short,
                autoload_with=conn,
            )
            temp_table_ref = sqlalchemy.Table(
                temp_table,
                metadata,
                autoload_with=conn,
            )
            insert_columns = [
                "time",
                "device_id",
                "expected_metric_id",
                "value",
                "confidence_tier",
                "confidence_codes",
                "version",
            ]

            select_from_temp = select(
                *(temp_table_ref.c[column] for column in insert_columns)
            )
            insert_stmt = insert(target_table).from_select(
                insert_columns,
                select_from_temp,
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[
                    target_table.c.time,
                    target_table.c.device_id,
                    target_table.c.expected_metric_id,
                ],
                set_={
                    "value": insert_stmt.excluded.value,
                    "confidence_tier": insert_stmt.excluded.confidence_tier,
                    "confidence_codes": insert_stmt.excluded.confidence_codes,
                    "version": insert_stmt.excluded.version,
                },
            )

            # Perform upsert then immediately drop the temp table so the
            # unique name is freed within long-lived / pooled sessions.
            conn.execute(upsert_stmt)
            conn.execute(text(f"DROP TABLE {temp_table}"))
            conn.commit()

            # --- Logging ---
            logging.info(f"... Uploaded {simulation_level} to proximal database")
