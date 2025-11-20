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

lambda_arn = os.getenv(f"LAMBDA_ARN_KPI_PIPELINE")


class KPIBackfillEvent(BaseModel):
    start: date = Field(default_factory=date.today)
    end: date = Field(default_factory=date.today)
    backfill_days: int = 1
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
    lambda_client = boto3.client("lambda", region_name="us-east-2")
    payload = json.dumps(event.model_dump(mode="json")).encode("utf-8")

    try:
        response = lambda_client.invoke(
            FunctionName=lambda_arn,
            InvocationType="Event",
            Payload=payload,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to invoke KPI backfill lambda",
        ) from exc

    if response.get("StatusCode") != 202:
        raise HTTPException(
            status_code=502,
            detail="Lambda invocation returned unexpected status",
        )

    return {"detail": "KPI backfill accepted"}
