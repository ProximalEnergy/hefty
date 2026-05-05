from fastapi import APIRouter, Depends

from app._dependencies.authentication import get_user
from app.v1.gis import equipment, weather

router = APIRouter(
    prefix="/gis",
    tags=["gis"],
    dependencies=[Depends(get_user)],
)
router.include_router(weather.router)
router.include_router(equipment.router)
