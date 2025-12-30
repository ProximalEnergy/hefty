import logging
from typing import Any

from app.v1.protected.pv_expected_energy.backfill.s01_lambda_call import (
    backfill_in_background,
)
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel


# --- Pydantic Models ---
class BackfillRequest(BaseModel):
    """todo"""

    single_diode_model: str | None = "DESOTO"
    soiling: str | None = "measured"
    degradation: str | None = "none"
    dc_wiring_to_combiner: str | None = "target_stc"
    dc_wiring_to_inverter: str | None = "target_stc"
    use_poa_only: bool | None = False
    use_median_irr_sensor: bool | None = False


# --- Routes ---
router = APIRouter(prefix="/backfill", tags=["backfill"])


@router.post(
    "",
    summary="backfill expected energy model",
)
def backfill_expected_energy_model(
    background_tasks: BackgroundTasks,
    request: BackfillRequest,
    energy_model_version: str,
    project_name_short: str,
    simulation_start: str,
    simulation_end: str,
):
    """Start dates of given projects:
            double_black_diamond: 2024-08-01
            sun_streams_4: 2024-12-01
            serrano: 2025-02-15

    Args:
        background_tasks: TODO: describe.
        request: TODO: describe.
        energy_model_version: TODO: describe.
        project_name_short: TODO: describe.
        simulation_start: TODO: describe.
        simulation_end: TODO: describe.
    """
    kwargs: dict[str, Any] = {}
    if request.single_diode_model is not None:
        kwargs["single_diode_model"] = request.single_diode_model
    if request.soiling is not None:
        kwargs["soiling"] = request.soiling
    if request.degradation is not None:
        kwargs["degradation"] = request.degradation
    if request.dc_wiring_to_combiner is not None:
        kwargs["dc_wiring_to_combiner"] = request.dc_wiring_to_combiner
    if request.dc_wiring_to_inverter is not None:
        kwargs["dc_wiring_to_inverter"] = request.dc_wiring_to_inverter
    if request.use_poa_only is not None:
        kwargs["use_poa_only"] = request.use_poa_only
    if request.use_median_irr_sensor is not None:
        kwargs["use_median_irr_sensor"] = request.use_median_irr_sensor

    logging.info("kwargs: %s", kwargs)

    background_tasks.add_task(
        backfill_in_background,
        energy_model_version=energy_model_version,
        project_name_short=project_name_short,
        simulation_start=simulation_start,
        simulation_end=simulation_end,
        **kwargs,
    )

    return 200
