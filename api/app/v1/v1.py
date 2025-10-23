from fastapi import APIRouter, Depends

from app.dependencies import get_user_data_async
from app.v1 import auth_test
from app.v1.admin import admin
from app.v1.ai.root_cause import router as root_cause_router
from app.v1.ai.voice_chat import router as voice_chat_router
from app.v1.analytics import analytics
from app.v1.commissioning import commissioning
from app.v1.development import development
from app.v1.feedback import feedback
from app.v1.gis import gis
from app.v1.operational import operational
from app.v1.protected import protected
from app.v1.ui import ui

router = APIRouter(prefix="/v1", dependencies=[Depends(get_user_data_async)])
router.include_router(admin.router)
router.include_router(analytics.router)
router.include_router(voice_chat_router)
router.include_router(root_cause_router)
router.include_router(commissioning.router)
router.include_router(development.router)
router.include_router(feedback.router)
router.include_router(gis.router)
router.include_router(operational.router)
router.include_router(protected.router)
router.include_router(ui.router)
router.include_router(auth_test.router)
