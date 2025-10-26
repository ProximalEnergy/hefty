from sqlalchemy.engine.row import Row
from sqlalchemy.orm import Session

from core import models


def get_spreadsheet_id(
    *,
    db: Session,
    project_name_short: str,
) -> str:
    google_sheet_id: Row[tuple[str | None]] | None = (
        db.query(models.Project.gsheet_id)
        .filter(models.Project.name_short == project_name_short)
        .first()
    )

    if google_sheet_id is not None:
        return str(google_sheet_id[0])
    else:
        raise ValueError("No project matches that name, or gsheet_id value is null")
