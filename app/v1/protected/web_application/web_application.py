from fastapi import APIRouter

from app import utils
from app.v1.protected.web_application.portfolio import portfolio
from app.v1.protected.web_application.projects import projects

router = APIRouter(
    prefix="/web-application",
    tags=["web-application"],
    include_in_schema=utils.get_include_in_schema(),
)

router.include_router(portfolio.router)
router.include_router(projects.router)
