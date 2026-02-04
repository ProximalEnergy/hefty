from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import utils
from app.dependencies import (
    get_async_db,
    get_project_api,
    get_project_db,
    get_project_db_async,
    tps_token_mgr_async,
)
from app.integrations.token_manager import TokenManager
from core import models

from .eec_bess_monthly import eec_bess_monthly as eec_bess_monthly_module

BESSMonthlyReportRequest = eec_bess_monthly_module.BESSMonthlyReportRequest

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    include_in_schema=utils.get_include_in_schema(),
)

# NOTE: FastAPI automatically adds imported paths to the router.
from . import (
    clearsky_filter,  # noqa: F401
    module_degradation,  # noqa: F401
    scada_telemetry_last_reported,  # noqa: F401
)


@router.post("/eec-bess-monthly-report")
async def post_eec_bess_monthly_report(
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_db: Annotated[AsyncSession, Depends(get_project_db_async)],
    project_db_sync: Annotated[Session, Depends(get_project_db)],
    request: BESSMonthlyReportRequest,
    tps_token: TokenManager = Depends(tps_token_mgr_async),
):
    """Generate a BESS monthly report.

    Args:
        project: The project for which to generate the report.
        db: Database session.
        project_db: Project database session.
        project_db_sync: Synchronous project database session.
        request: BESS monthly report request data including month, strategies,
            and commentary.
        tps_token: TPS API authentication token.
    """
    generate_eec_bess_monthly_report = (
        eec_bess_monthly_module.generate_eec_bess_monthly_report
    )
    access_token = await tps_token.get_token()

    await generate_eec_bess_monthly_report(
        project=project,
        db=db,
        project_db=project_db,
        project_db_sync=project_db_sync,
        request=request,
        tps_token=access_token,
    )
