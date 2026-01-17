import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import dependencies, interfaces
from app._crud.projects import pv_budgeted as crud

router = APIRouter(
    prefix="/projects/{project_id}/pv-budgeted", tags=["project - pv budgeted"]
)


@router.get("/series", response_model=list[interfaces.PVBudgetedSeries])
def list_pv_budgeted_series(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project_id: uuid.UUID,
):
    """todo

    Args:
        project_db: TODO: describe.
        project_id: TODO: describe.
    """
    series = crud.list_series(project_db=project_db, project_id=project_id)

    result = [
        interfaces.PVBudgetedSeries(
            pv_budgeted_series_id=s.pv_budgeted_series_id,
            p_value=s.p_value,
            frequency=s.frequency,
            soiling_mode=s.soiling_mode,
            soiling_fixed_percentage=s.soiling_fixed_percentage,
            tmy_source=s.tmy_source,
            model_version=s.model_version,
            filename=s.filename,
        )
        for s in series
    ]
    return result


@router.post("/series", response_model=interfaces.PVBudgetedSeries)
def create_pv_budgeted_series(
    payload: interfaces.PVBudgetedSeriesIn,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project_id: uuid.UUID,
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """todo

    Args:
        payload: TODO: describe.
        project_db: TODO: describe.
        project_id: TODO: describe.
        user_data: TODO: describe.
    """
    series = crud.create_series(
        project_db=project_db,
        series_in=payload,
        company_id=user_data.company_id,
        project_id=project_id,
    )
    return interfaces.PVBudgetedSeries(
        pv_budgeted_series_id=series.pv_budgeted_series_id,
        p_value=series.p_value,
        frequency=series.frequency,
        soiling_mode=series.soiling_mode,
        soiling_fixed_percentage=series.soiling_fixed_percentage,
        tmy_source=series.tmy_source,
        model_version=series.model_version,
        filename=series.filename,
    )


@router.get("/data", response_model=list[interfaces.PVBudgetedDataRow])
def get_pv_budgeted_data(
    pv_budgeted_series_id: int,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        pv_budgeted_series_id: TODO: describe.
        project_db: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    if (
        crud.get_series(
            project_db=project_db, pv_budgeted_series_id=pv_budgeted_series_id
        )
        is None
    ):
        raise HTTPException(status_code=404, detail="Series not found")
    rows = crud.fetch_data(
        project_db=project_db,
        pv_budgeted_series_id=pv_budgeted_series_id,
        start=start,
        end=end,
    )
    return [
        interfaces.PVBudgetedDataRow(
            time_stamp=r.time,
            poi_ac_power=r.poi_ac_power,
            ghi=r.ghi,
            poa=r.poa,
            temperature=r.temperature,
            soiling_percentage=r.soiling_percentage,
        )
        for r in rows
    ]


@router.delete("/series/{pv_budgeted_series_id}")
def delete_pv_budgeted_series(
    pv_budgeted_series_id: int,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    # Check if series exists
    """todo

    Args:
        pv_budgeted_series_id: TODO: describe.
        project_db: TODO: describe.
    """
    if (
        crud.get_series(
            project_db=project_db, pv_budgeted_series_id=pv_budgeted_series_id
        )
        is None
    ):
        raise HTTPException(status_code=404, detail="Series not found")

    # Delete the series and all associated data
    success = crud.delete_series(
        project_db=project_db,
        pv_budgeted_series_id=pv_budgeted_series_id,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete series")

    return {"message": "Series deleted successfully"}


@router.post("/data/bulk-upsert")
def bulk_upsert_pv_budgeted_data(
    payload: interfaces.PVBudgetedBulkUpsertRequest,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project_id: uuid.UUID,
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """todo

    Args:
        payload: TODO: describe.
        project_db: TODO: describe.
        project_id: TODO: describe.
        user_data: TODO: describe.
    """
    series_id = payload.pv_budgeted_series_id
    if series_id is None:
        if payload.series is None:
            raise HTTPException(status_code=400, detail="Series metadata required")
        created = crud.create_series(
            project_db=project_db,
            series_in=payload.series,
            company_id=user_data.company_id,
            project_id=project_id,
        )
        series_id = created.pv_budgeted_series_id
    else:
        # Update metadata if provided
        if payload.series is not None:
            updated = crud.update_series(
                project_db=project_db,
                pv_budgeted_series_id=series_id,
                series_in=payload.series,
            )
            if updated is None:
                raise HTTPException(status_code=404, detail="Series not found")

    if crud.get_series(project_db=project_db, pv_budgeted_series_id=series_id) is None:
        raise HTTPException(status_code=404, detail="Series not found")

    # Basic input validation is already enforced by Pydantic; ensure non-empty rows
    if not payload.rows:
        return {"pv_budgeted_series_id": series_id, "upserted": 0}

    count = crud.bulk_upsert_data(
        project_db=project_db,
        pv_budgeted_series_id=series_id,
        rows=payload.rows,
    )
    return {"pv_budgeted_series_id": series_id, "upserted": count}
