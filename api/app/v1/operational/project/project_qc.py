from fastapi import APIRouter

from app.v1.operational.project.qc import combiner_swaps

router = APIRouter(
    prefix="/projects/{project_id}/qc",
    tags=["qc"],
)
router.include_router(combiner_swaps.router)


@router.get("/health")
async def health():
    """todo"""
    return {"status": "ok"}
