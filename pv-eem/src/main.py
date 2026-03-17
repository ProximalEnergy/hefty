import asyncio
import logging
import traceback
from typing import Any, cast

import psycopg2
import sentry_sdk
from _utils.environment_variables import load_environment_variables
from _utils.logger import setup_logger
from p00_parse_input.s00_parse_input import ParsedInputs
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p01_get_data.class_simulation_inputs import SimulationInputs
from p02_simulation._utils.known_exception import KnownException
from p02_simulation.c_simulate_project import simulate_project
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner
from p02_simulation.p4_dc_iv.s02_single_diode_params import ModelSingleDiode
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import (
    ModelDCWiringToCombiner,
)
from p02_simulation.p5_inverter.c_inverter import InverterPower
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import ModelDCWiringToInverter
from p02_simulation.p6_transformer.c_transformer import TransformerPower
from p02_simulation.p8_poi.c_poi import ProjectPower
from p03_export.c_export import export_simulation_results
from p04_error_handling.c_handle_errors import handle_errors
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration


def before_send(event, hint):
    """Filter out KnownException from being sent to Sentry"""
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if isinstance(exc_value, KnownException):
            return None
        elif isinstance(exc_value, KeyboardInterrupt):
            return None
    return event


# Only initialize Sentry if:
# 1. Environment is PROD
# 2. Running in AWS Lambda (not locally
ENVIRONMENT_VARIABLES = load_environment_variables()
ENVIRONMENT = ENVIRONMENT_VARIABLES.environment
is_aws_lambda = ENVIRONMENT_VARIABLES.is_aws_lambda

if ENVIRONMENT == "PROD" and is_aws_lambda:
    sentry_sdk.init(
        dsn="https://18322ab152d66953ffb151707e313f37@o4506555874672640.ingest.us.sentry.io/4509548984795136",
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/
        send_default_pii=True,
        integrations=[AwsLambdaIntegration()],
        before_send=before_send,
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run lambda_handler."""
    _ = context

    try:
        # --- Setup Logging ---
        setup_logger()

        # Add this at the beginning of your lambda_handler function
        # --- Parse Inputs ---
        parsed_inputs = ParsedInputs.parse_inputs(event)
        project_name_short = parsed_inputs.project_name_short
        simulation_temporal_mode = parsed_inputs.simulation_temporal_mode
        simulation_start = parsed_inputs.simulation_start
        simulation_end = parsed_inputs.simulation_end
        kwargs = parsed_inputs.kwargs

        # --- Run the simulation ---
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            get_expected_energy(
                project_name_short=project_name_short,
                simulation_temporal_mode=simulation_temporal_mode,
                simulation_start=simulation_start,
                simulation_end=simulation_end,
                **kwargs,
            )
        )

        return result
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        logging.error(traceback.format_exc())  # This logs the full traceback
        raise  # Re-raise the exception to see it in Lambda's response


async def get_expected_energy(
    project_name_short: str,
    simulation_temporal_mode: SimulationTemporalMode,
    simulation_start: str | None = None,
    simulation_end: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Get expected energy for all PV and PV+Storage projects"""
    try:
        # --- Get Simulation Config ---
        simulation_inputs: SimulationInputs = await SimulationInputs.from_proximal_db(
            project_name_short=project_name_short,
            simulation_temporal_mode=simulation_temporal_mode,
            simulation_start=simulation_start,
            simulation_end=simulation_end,
            **kwargs,
        )

        # --- Define the Simulation Generator ---
        simulation = simulate_project(inputs=simulation_inputs)

        # --- Run the simulation ---
        poai: PlaneOfArrayIrradiance = cast(PlaneOfArrayIrradiance, next(simulation))
        export_simulation_results(
            results=poai,
            project_name_short=project_name_short,
            simulation_start=simulation_start,
            simulation_config=simulation_inputs.simulation_config,
            engine=simulation_inputs.engine,
            version=simulation_inputs.version,
            ENVIRONMENT=simulation_inputs.ENVIRONMENT,
        )
        # DEBUGGING
        # poai.to_csv(target_string_id=0)

        combiners: PowerAtCombiner = cast(PowerAtCombiner, next(simulation))
        export_simulation_results(
            results=combiners,
            project_name_short=project_name_short,
            simulation_start=simulation_start,
            simulation_config=simulation_inputs.simulation_config,
            engine=simulation_inputs.engine,
            version=simulation_inputs.version,
            ENVIRONMENT=simulation_inputs.ENVIRONMENT,
        )

        inverters: InverterPower = cast(InverterPower, next(simulation))
        export_simulation_results(
            results=inverters,
            project_name_short=project_name_short,
            simulation_start=simulation_start,
            simulation_config=simulation_inputs.simulation_config,
            engine=simulation_inputs.engine,
            version=simulation_inputs.version,
            ENVIRONMENT=simulation_inputs.ENVIRONMENT,
        )

        transformers: TransformerPower = cast(TransformerPower, next(simulation))
        if simulation_inputs.ENVIRONMENT == "DEV":
            export_simulation_results(
                results=transformers,
                project_name_short=project_name_short,
                simulation_start=simulation_start,
                simulation_config=simulation_inputs.simulation_config,
                engine=simulation_inputs.engine,
                version=simulation_inputs.version,
                ENVIRONMENT=simulation_inputs.ENVIRONMENT,
            )

        poi: ProjectPower = cast(ProjectPower, next(simulation))
        export_simulation_results(
            results=poi,
            project_name_short=project_name_short,
            simulation_start=simulation_start,
            simulation_config=simulation_inputs.simulation_config,
            engine=simulation_inputs.engine,
            version=simulation_inputs.version,
            ENVIRONMENT=simulation_inputs.ENVIRONMENT,
        )

        # --- Finish ---
        result = {"status_code": 200, "message": "Simulation complete"}

    # --- Known Errors ---
    except KnownException as ke:
        logging.info(f"Known exception occurred: {ke}")
        result = {
            "status_code": ke.error_type.value,
            "message": f"Known Exception: {ke.error_type.name}, {ke.message}",
        }

    # --- Unknown / Un-expected Errors ---
    except Exception as e:
        if isinstance(e, ExceptionGroup):
            db_errors, non_db_errors = e.split(psycopg2.OperationalError)
            if db_errors is not None and non_db_errors is None:
                logging.warning(
                    "DB retry event: psycopg2 OperationalError in TaskGroup",
                    exc_info=db_errors,
                )
                result = {
                    "status_code": 503,
                    "message": "Retryable database connectivity error",
                }
                return result

        handle_errors(
            message=f"""
                Simulation Failed:
                Project: {project_name_short}
                Simulation Mode: {simulation_temporal_mode}
                Simulation Start: {simulation_start}
                Simulation End: {simulation_end}
                Error: {e}
            """,
        )
        result = {"status_code": 500, "message": str(e)}
        logging.error(f"Unexpected error: {e}")
        logging.error(traceback.format_exc())

    return result


# --- For manual use only ---
if __name__ == "__main__":
    # --- Imports ---
    # --- Dataframe Config ---
    import pandas as pd
    from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
    from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
    from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)

    import polars as pl

    pl.Config.set_tbl_rows(100)
    pl.Config.set_tbl_cols(-1)

    # --- Logger ---
    setup_logger(level=logging.INFO, environment="DEV")

    # --- Main Simulation ---
    result = asyncio.run(
        get_expected_energy(
            # ARGS
            project_name_short="sigurd",  # noqa: hardcoded-name-short
            simulation_temporal_mode=SimulationTemporalMode.WINDOW,
            simulation_start="2025-10-01 00:00:00",
            simulation_end="2025-10-01 23:55:00",
            # KWARGS
            sun_position_offset=0,
            use_poa_only=False,
            use_median_irr_sensor=False,
            soiling=ModelSoiling.NONE,
            degradation=ModelDegradation.WARRANTED,
            single_diode_model=ModelSingleDiode.PVWATTS,
            circumsolar=ModelCircumsolar.DIFFUSE,
            dc_wiring_to_combiner=ModelDCWiringToCombiner.TARGET_STC,
            dc_wiring_to_inverter=ModelDCWiringToInverter.TARGET_STC,
        )
    )

    from pprint import pformat

    logging.info("%s", pformat(result))
