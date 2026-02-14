from app.v1.commissioning.eem import system
from fastapi import APIRouter

# --- Routes ---
router = APIRouter(prefix="/commissioning", tags=["commissioning"])
router.include_router(system.router)
