import asyncio

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import interfaces
from app.domain.eem.google_sheet.read.s01_read_gsheet import (
    read_google_sheet,
)
from app.domain.eem.google_sheet.read.s02_parse_equipment_modules import (
    parse_equipment_modules,
)
from app.domain.eem.google_sheet.read.s03_parse_equipment_rackings import (
    parse_equipment_rackings,
)
from app.domain.eem.google_sheet.read.s04_parse_equipment_inverters import (
    parse_equipment_inverters,
)
from app.domain.eem.google_sheet.read.s05_parse_devices_combiners import (
    parse_devices_combiners,
)
from app.domain.eem.google_sheet.read.s06_parse_devices_inverters import (
    parse_devices_inverters,
)
from app.domain.eem.google_sheet.read.s08_add_devices_blocks import (
    add_devices_blocks,
)
from app.domain.eem.google_sheet.read.s09_add_devices_circuits import (
    add_devices_circuits,
)
from app.domain.eem.google_sheet.read.s10_build_system import build_system
from app.domain.eem.google_sheet.read.s11_export import export_system


async def import_google_sheet(
    *,
    db: AsyncSession,
    project_db: Session,
    project: interfaces.Project,
):
    # --- Read data ---
    """todo

    Args:
        db: Description for db.
        project_db: Description for project_db.
        project: Description for project.
    """
    project_name_short = project.name_short
    google_sheet_id: str | None = project.gsheet_id
    if google_sheet_id is None:
        raise HTTPException(status_code=404, detail="Google Sheet ID not found")
    system: pd.DataFrame = await asyncio.to_thread(
        read_google_sheet,
        spreadsheet_id=google_sheet_id,
    )

    # --- Parse Equipment Ids ---
    system = await parse_equipment_modules(
        db=db,
        system=system,
    )
    system = await parse_equipment_rackings(
        db=db,
        system=system,
    )
    system = await parse_equipment_inverters(
        db=db,
        system=system,
    )

    # --- Parse Device Ids ---
    system = await parse_devices_combiners(
        project_db=project_db,
        system=system,
    )

    system = await parse_devices_inverters(
        project_db=project_db,
        system=system,
    )

    # --- Add Devices that don't need parsing ---
    system = await add_devices_blocks(
        project_db=project_db,
        system=system,
    )
    system = await add_devices_circuits(
        project_db=project_db,
        system=system,
    )

    # --- Build System ---
    system = await asyncio.to_thread(
        build_system,
        system=system,
    )

    # --- Export ---
    await asyncio.to_thread(
        export_system,
        system=system,
        project_name_short=project_name_short,
    )

    return 200
