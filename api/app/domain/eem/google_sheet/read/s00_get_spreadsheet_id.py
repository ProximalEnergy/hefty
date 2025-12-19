from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_spreadsheet_id(
    *,
    db: AsyncSession,
    project_name_short: str,
) -> str:
    """todo

    Args:
        db: TODO: describe.
        project_name_short: TODO: describe.
    """
    query = select(models.Project.gsheet_id).where(
        models.Project.name_short == project_name_short,
    )
    result = await db.execute(query)
    google_sheet_id = result.scalar_one_or_none()

    if google_sheet_id is None:
        raise ValueError("No project matches that name, or gsheet_id value is null")

    return str(google_sheet_id)
