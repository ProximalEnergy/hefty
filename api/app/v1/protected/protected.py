import json
import os
from datetime import date

import boto3
import dotenv
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import dependencies, utils
from app.v1.protected import system
from app.v1.protected.deletions import deletions
from app.v1.protected.internal_comms import internal_comms
from app.v1.protected.pv_expected_energy import pv_expected_energy
from app.v1.protected.web_application import web_application

dotenv.load_dotenv()

router = APIRouter(
    prefix="/protected",
    tags=["protected"],
    include_in_schema=utils.get_include_in_schema(),
)
router.include_router(web_application.router)
router.include_router(system.router)
router.include_router(pv_expected_energy.router)
router.include_router(deletions.router)
router.include_router(internal_comms.router)

step_function_arn = os.getenv("STEP_FUNCTION_ARN_KPI_PIPELINE")


class KPIBackfillEvent(BaseModel):
    """Payload for a KPI backfill request."""

    start: date = Field(default_factory=date.today)
    end: date = Field(default_factory=date.today)
    backfill_days: int = 0
    project_name_short_list: list[str]
    kpi_type_ids: list[int] | None = None


@router.post(
    "/kpi-backfill",
    status_code=202,
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
def trigger_kpi_backfill_lambda(
    *,
    event: KPIBackfillEvent,
):
    """Trigger the KPI backfill step function.

    Args:
        event: Payload describing the backfill parameters and targets.
    """
    stepfunctions_client = boto3.client("stepfunctions", region_name="us-east-2")
    input_payload = json.dumps(event.model_dump(mode="json"))

    try:
        response = stepfunctions_client.start_execution(
            stateMachineArn=step_function_arn,
            input=input_payload,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to start KPI backfill step function",
        ) from exc

    if not response.get("executionArn"):
        raise HTTPException(
            status_code=502,
            detail="Step function execution returned unexpected response",
        )

    return {"detail": "KPI backfill accepted"}
