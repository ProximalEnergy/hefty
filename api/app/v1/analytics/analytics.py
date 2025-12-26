################################################################################
#                                                                              #
#  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  #
#  !                                                                        !  #
#  !  DEPRECATION WARNING: This file is deprecated and will be removed      !  #
#  !  in a future release.  Please do not add new code here.  All new       !  #
#  !  additions should be placed in protected.                              !  #
#  !                                                                        !  #
#  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  #
#                                                                              #
################################################################################
from fastapi import APIRouter, Depends

from app import dependencies
from app.utils import get_include_in_schema
from app.v1.analytics.gis import router as gis_router

router = APIRouter(
    prefix="/analytics/{project_id}",
    dependencies=[
        Depends(dependencies.check_project_access_async),
    ],
    tags=["analytics"],
    include_in_schema=get_include_in_schema(),
)
router.include_router(gis_router)
