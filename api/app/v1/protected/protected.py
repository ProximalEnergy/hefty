import json
import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

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
scheduler_role_arn = os.getenv("EVENT_BRIDGE_SCHEDULER_START_SFN_ROLE")


class KPIBackfillEvent(BaseModel):
    """Payload for a KPI backfill request."""

    start: date = Field(default_factory=date.today)
    end: date = Field(default_factory=date.today)
    backfill_days: int = 0
    days_per_chunk: int = 1
    project_name_short_list: list[str] | None = None
    kpi_type_ids: list[int] | None = None


class ScheduledKPIBackfillEvent(KPIBackfillEvent):
    """Payload for scheduling a KPI backfill request."""

    scheduled_for: datetime


def _utc_now() -> datetime:
    """Get the current UTC timestamp."""
    return datetime.now(tz=UTC)


def _validate_scheduled_for(*, scheduled_for: datetime) -> datetime:
    """Validate scheduled execution timestamp and return UTC value.

    Args:
        scheduled_for: The requested execution time with timezone offset.
    """
    if (
        scheduled_for.tzinfo is None
        or scheduled_for.tzinfo.utcoffset(scheduled_for) is None
    ):
        raise HTTPException(
            status_code=422,
            detail="scheduled_for must include a timezone offset",
        )

    scheduled_for_utc = scheduled_for.astimezone(UTC)
    now_utc = _utc_now()

    if scheduled_for_utc <= now_utc:
        raise HTTPException(
            status_code=422,
            detail="scheduled_for must be in the future",
        )

    if scheduled_for_utc < now_utc + timedelta(seconds=60):
        raise HTTPException(
            status_code=422,
            detail="scheduled_for must be at least 60 seconds from now",
        )

    if scheduled_for_utc > now_utc + timedelta(days=7):
        raise HTTPException(
            status_code=422,
            detail="scheduled_for cannot be more than 7 days in the future",
        )

    return scheduled_for_utc


def _schedule_expression_at_utc(*, scheduled_for_utc: datetime) -> str:
    """Build EventBridge Scheduler at() expression string in UTC.

    Args:
        scheduled_for_utc: Time normalized to UTC.
    """
    timestamp = scheduled_for_utc.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
    return f"at({timestamp})"


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


@router.post(
    "/kpi-backfill/schedule",
    status_code=202,
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
def schedule_kpi_backfill(
    *,
    event: ScheduledKPIBackfillEvent,
):
    """Schedule a one-time KPI backfill step function execution.

    Args:
        event: Payload describing the backfill and schedule execution time.
    """
    if not step_function_arn:
        raise HTTPException(
            status_code=503,
            detail="Missing STEP_FUNCTION_ARN_KPI_PIPELINE configuration",
        )

    if not scheduler_role_arn:
        raise HTTPException(
            status_code=503,
            detail="Missing EVENT_BRIDGE_SCHEDULER_START_SFN_ROLE configuration",
        )

    scheduled_for_utc = _validate_scheduled_for(scheduled_for=event.scheduled_for)
    scheduler_client = boto3.client("scheduler", region_name="us-east-2")
    payload = event.model_dump(mode="json", exclude={"scheduled_for"})
    schedule_name = f"kpi-backfill-{uuid4().hex}"

    try:
        response = scheduler_client.create_schedule(
            Name=schedule_name,
            ScheduleExpression=_schedule_expression_at_utc(
                scheduled_for_utc=scheduled_for_utc,
            ),
            ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 5},
            ActionAfterCompletion="DELETE",
            Target={
                "Arn": step_function_arn,
                "RoleArn": scheduler_role_arn,
                "Input": json.dumps(payload),
            },
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to create KPI backfill schedule",
        ) from exc

    return {
        "detail": "KPI backfill schedule accepted",
        "schedule_name": schedule_name,
        "schedule_arn": response.get("ScheduleArn"),
        "scheduled_for": scheduled_for_utc.isoformat(),
    }
