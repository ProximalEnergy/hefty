from app import dependencies
from app.utils import get_include_in_schema
from app.v1.protected.pv_expected_energy.backfill import c_backfill as backfill
from app.v1.protected.pv_expected_energy.plot import plot
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/{project_id}/pv-expected-energy",
    dependencies=[
        Depends(dependencies.check_project_access_async),
    ],
    tags=["pv-expected"],
    include_in_schema=get_include_in_schema(),
)

router.include_router(backfill.router)
router.include_router(plot.router)


@router.get("/health")
def health_check():
    return {"status": "ok"}
