from fastapi import APIRouter

from app import utils
from app.v1.protected.deletions import delete_project

router = APIRouter(
    prefix="/deletions",
    tags=["deletions"],
    include_in_schema=utils.get_include_in_schema(),
)

router.include_router(delete_project.router)
