from fastapi import APIRouter

import app.v1.protected.web_application.projects.project_tag_explorer as project_tag_explorer
from app import utils
from app.v1.protected.web_application.projects.custom_dash import custom_dash
from app.v1.protected.web_application.projects.device_details import device_details
from app.v1.protected.web_application.projects.equipment_analysis import (
    equipment_analysis,
)
from app.v1.protected.web_application.projects.events import events
from app.v1.protected.web_application.projects.real_time import real_time

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["projects"],
    include_in_schema=utils.get_include_in_schema(),
)

router.include_router(equipment_analysis.router)
router.include_router(device_details.router)
router.include_router(project_tag_explorer.router)
router.include_router(real_time.router)
router.include_router(events.router)
router.include_router(custom_dash.router)
