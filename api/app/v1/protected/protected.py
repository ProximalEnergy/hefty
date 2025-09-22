from fastapi import APIRouter

from app import utils
from app.v1.protected import system
from app.v1.protected.deletions import deletions
from app.v1.protected.internal_comms import internal_comms
from app.v1.protected.pv_expected_energy import pv_expected_energy
from app.v1.protected.web_application import web_application

router = APIRouter(
    prefix="/protected",
    tags=["protected"],
    include_in_schema=utils.get_include_in_schema(),
)
router.include_router(web_application.router)
router.include_router(system.router)
router.include_router(pv_expected_energy.router)
router.include_router(deletions.router)
router.include_router(internal_comms.router)
