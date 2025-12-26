from fastapi import APIRouter, Depends

from app import dependencies
from app.v1.gis import combiner, hail, weather

get_user_data_async = [Depends(dependencies.get_user_data_async)]

router = APIRouter(
    prefix="/gis",
    tags=["gis"],
    dependencies=get_user_data_async,
)
router.include_router(hail.router)
router.include_router(weather.router)
router.include_router(combiner.router)
