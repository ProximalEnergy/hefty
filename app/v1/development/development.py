from fastapi import APIRouter, Depends

from app import dependencies
from app.v1.development import ercot

router = APIRouter(
    prefix="/development",
    tags=["development"],
    dependencies=[Depends(dependencies.get_user_data_async)],
)
router.include_router(ercot.router)
