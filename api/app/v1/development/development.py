from fastapi import APIRouter, Depends

from app._dependencies.authentication import get_user
from app.v1.development import ercot, ptp

router = APIRouter(
    prefix="/development",
    tags=["development"],
    dependencies=[Depends(get_user)],
)
router.include_router(ercot.router)
router.include_router(ptp.router)
