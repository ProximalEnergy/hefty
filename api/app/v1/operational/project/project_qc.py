from fastapi import APIRouter, Depends

from app.dependencies import check_project_access_async
from app.v1.operational.project.qc import combiner_swaps

router = APIRouter(
    prefix="/projects/{project_id}/qc",
    tags=["qc"],
    dependencies=[Depends(check_project_access_async)],
)
router.include_router(combiner_swaps.router)
