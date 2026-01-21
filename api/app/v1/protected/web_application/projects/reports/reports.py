from fastapi import APIRouter, Depends

from app import dependencies, utils

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(dependencies.check_project_access_async)],
    include_in_schema=utils.get_include_in_schema(),
)

# NOTE: FastAPI automatically adds imported paths to the router.
from . import (
    clearsky_filter,  # noqa: F401
    module_degradation,  # noqa: F401
    scada_telemetry_last_reported,  # noqa: F401
)
