from app.dependencies import check_project_access_async
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/projects/{project_id}/system",
    tags=["system"],
    dependencies=[Depends(check_project_access_async)],
)
