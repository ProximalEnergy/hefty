import datetime
from typing import Literal

import core.models as models
import pandas as pd
from core.db_query import OutputType
from core.enumerations import DeviceType
from core.model_list import ModelList
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import utils
from app.dependencies import get_project_api, get_project_db, get_project_db_async

router = APIRouter(
    prefix="/events",
    tags=["events"],
    include_in_schema=utils.get_include_in_schema(),
)


class EventMetrics(BaseModel):
    """todo"""

    device_type_id: int
    device_type_name: str
    MTBF_hours: float | None
    MTTR_hours: float | None
    failure_count: int
    unavailability_contribution: float


class DeviceTotals(BaseModel):
    """todo"""

    device_type_id: int
    device_ids: list[int]
    device_names: list[str]
    total_failures: list[int]
    total_hours: list[float]


class EventMetaData(BaseModel):
    """todo"""

    metrics: list[EventMetrics]
    daily_totals: dict[str, list[str] | list[int]]
    device_totals: list[DeviceTotals]


def _ensure_tz_aware(*, ts: pd.Series, tz: str) -> pd.Series:
    """Convert a datetime series to timezone-aware (project tz).
        - If any values are tz-aware already, use tz_convert.
        - If entirely naive or entirely None, localize.
        Mirrors original try/except behavior but clearer and safer.

    Args:
        ts: TODO: describe.
        tz: TODO: describe.
    """
    s = pd.to_datetime(ts)
    if s.dt.tz is None:
        # All-naive or all-None → localize
        return s.dt.tz_localize(tz)
    # Already aware → convert
    return s.dt.tz_convert(tz)


def _clip_to_window(  # nosemgrep: python-enforce-keyword-only-args
    s: pd.Series,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.Series:
    """todo

    Args:
        s: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    return s.clip(lower=start, upper=end)  # type: ignore


@router.get("/meta", response_model=EventMetaData)
async def get_meta_analysis(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(get_project_db),
    project_db_async: AsyncSession = Depends(get_project_db_async),
    project: models.Project = Depends(get_project_api),
):
    # -----------------------
    # Window setup (unchanged outputs)
    # -----------------------
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        project_db_async: TODO: describe.
        project: TODO: describe.
    """
    if not start or not end:
        start = pd.Timestamp.now(tz=project.time_zone).normalize() - pd.Timedelta(
            days=1
        )
        end = start + pd.Timedelta(days=2)

    total_hours = (end - start).total_seconds() / 3600
    tz = project.time_zone
    tz_start = pd.Timestamp(start).tz_convert(tz)
    tz_end = pd.Timestamp(end).tz_convert(tz)

    # -----------------------
    # Source data
    # -----------------------
    event_data = core.crud.project.events.get_windowed_events(start=start, end=end)
    devices = core.crud.project.devices.get_project_devices(
        project_db
    ).pandas_dataframe(index="device_id")

    df = await event_data.get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )
    df = df.copy()

    # Time columns → project tz (preserve original behavior for None/naive)
    df["time_start"] = _ensure_tz_aware(ts=df["time_start"], tz=tz)
    # Special case kept: if all time_end are None, localize; else convert
    time_end_series = pd.to_datetime(df["time_end"])
    if time_end_series.notna().any():
        df["time_end"] = _ensure_tz_aware(ts=df["time_end"], tz=tz)
    else:
        df["time_end"] = time_end_series.dt.tz_localize(tz)

    # Daily counts (based on original, pre-clip starts)
    df["day"] = df["time_start"].dt.floor("D")
    counts_by_day = df.groupby("day").size()
    counts_by_day.index = (
        pd.to_datetime(counts_by_day.index).tz_localize(None).strftime("%Y-%m-%d")
    )

    # Flag originally-open events before clip/fill
    df["is_open"] = df["time_end"].isna()

    # Clip to analysis window (keep fill for availability math & MTBF)
    df["time_start"] = _clip_to_window(df["time_start"], tz_start, tz_end)
    df["time_end"] = df["time_end"].fillna(tz_end)
    df["time_end"] = _clip_to_window(df["time_end"], tz_start, tz_end)

    df = df.sort_values(by=["device_id", "time_start"])

    # -----------------------
    # Device/linkage data
    # -----------------------
    # Use vectorized mapping off the devices index (faster than row-wise lambdas)
    capacity_ac_map = devices["capacity_ac"]
    capacity_dc_map = devices["capacity_dc"]
    dtype_map = devices["device_type_id"]

    df["capacity_ac"] = df["device_id"].map(capacity_ac_map)
    df["capacity_dc"] = df["device_id"].map(capacity_dc_map)
    df["device_type_id"] = df["device_id"].map(dtype_map)

    project_cap = project.capacity_ac * 1000
    if project_cap == 0:
        project_cap = project.poi * 1000

    # Override capacity for project-level events
    df.loc[df["device_type_id"] == DeviceType.METER, "capacity_ac"] = project_cap

    # -----------------------
    # Durations & unavailability (default)
    # -----------------------
    df["hours_elapsed"] = (df["time_end"] - df["time_start"]).dt.total_seconds() / 3600
    df["unavailability_contribution"] = (
        df["hours_elapsed"] * df["capacity_ac"] / (project_cap * total_hours)
    )

    # -----------------------
    # Device totals (include devices with zero events for present types)
    # -----------------------
    agg = (
        df.reset_index(drop=False)
        .groupby(["device_type_id", "device_id"], as_index=False)
        .agg(total_failures=("event_id", "count"), total_hours=("hours_elapsed", "sum"))
        .sort_values(["device_type_id", "device_id"])
    )

    device_totals: list[DeviceTotals] = []

    # Types present in aggregation
    types_present = pd.Index(agg["device_type_id"].unique())

    # Device list for those types
    devs = devices.reset_index().loc[
        lambda d: d["device_type_id"].isin(types_present),
        ["device_id", "device_type_id"],
    ]

    # Complete (device_type_id, device_id) grid for those types
    full_idx = pd.MultiIndex.from_frame(devs[["device_type_id", "device_id"]])

    completed_agg = (
        agg.set_index(["device_type_id", "device_id"])
        .reindex(full_idx, fill_value=0)
        .reset_index()
        .astype({"total_failures": "int64", "total_hours": "float64"})
        .sort_values(["device_type_id", "device_id"])
    )

    # Device names (with 'Project' override for type 5)
    name_map = devices["name_long"].to_dict()
    completed_agg["device_name"] = completed_agg["device_id"].map(name_map)
    completed_agg.loc[completed_agg["device_type_id"] == 5, "device_name"] = "Project"

    for dtid, sub in completed_agg.groupby("device_type_id", sort=True):
        device_totals.append(
            DeviceTotals(
                device_type_id=int(dtid),  # type: ignore
                device_ids=sub["device_id"].astype(int).tolist(),
                device_names=sub["device_name"].tolist(),
                total_failures=sub["total_failures"].astype(int).tolist(),
                total_hours=sub["total_hours"].astype(float).tolist(),
            )
        )

    # -----------------------
    # DC-level adjustment for combiners (type 9)
    # -----------------------
    if (df["device_type_id"] == 9).any():
        parent_map = devices["parent_device_id"].astype("Int64")
        parent_ac = devices["capacity_ac"]
        parent_dc = devices["capacity_dc"]

        cb_df = df.loc[df["device_type_id"] == 9].copy()
        cb_df["parent_device_id"] = cb_df["device_id"].map(parent_map).astype(int)
        cb_df["parent_capacity_ratio"] = cb_df["parent_device_id"].map(
            parent_ac
        ) / cb_df["parent_device_id"].map(parent_dc)

        cb_df["unavailability_contribution"] = (
            cb_df["hours_elapsed"]
            * cb_df["capacity_dc"]
            * cb_df["parent_capacity_ratio"]
        ) / (project_cap * total_hours)

        df.loc[cb_df.index, "unavailability_contribution"] = cb_df[
            "unavailability_contribution"
        ]

    # -----------------------
    # Global nuisance filter — drop events < 1 hour for downstream calcs
    # -----------------------
    df = df.loc[df["hours_elapsed"] >= 1].copy()

    # -----------------------
    # MTBF (per device → per type), only if >1 event at the type level
    # -----------------------
    df["time_diff"] = df.groupby("device_id")["time_start"].diff()
    mtbf = (
        df.groupby("device_id", as_index=False)["time_diff"]
        .mean()
        .rename(columns={"time_diff": "MTBF"})  # type: ignore
    )
    mtbf["MTBF_hours"] = mtbf["MTBF"].dt.total_seconds() / 3600
    mtbf["device_type_id"] = mtbf["device_id"].map(dtype_map)
    mtbf_by_type = mtbf.groupby("device_type_id", as_index=False)["MTBF_hours"].mean()

    # -----------------------
    # MTTR — exclude ongoing events (use original is_open flag)
    # -----------------------
    df_mttr = df.loc[~df["is_open"]].copy()
    df_mttr["repair_time"] = (
        df_mttr["time_end"] - df_mttr["time_start"]
    ).dt.total_seconds() / 3600
    mttr = (
        df_mttr.groupby("device_id", as_index=False)["repair_time"]
        .mean()
        .rename(columns={"repair_time": "MTTR_hours"})  # type: ignore
    )
    mttr["device_type_id"] = mttr["device_id"].map(dtype_map)
    mttr_by_type = mttr.groupby("device_type_id", as_index=False)["MTTR_hours"].mean()

    # -----------------------
    # Failure counts & unavailability by type (post-<1h filter)
    # -----------------------
    failure_count_by_type = (
        df.groupby("device_type_id").size().reset_index(name="failure_count")
    )
    unavail_by_type = df.groupby("device_type_id", as_index=False)[
        "unavailability_contribution"
    ].sum()

    # -----------------------
    # Combine aggregates on device_type_id
    # -----------------------
    agg_types = (
        mtbf_by_type.merge(mttr_by_type, on="device_type_id", how="outer")
        .merge(failure_count_by_type, on="device_type_id", how="outer")
        .merge(unavail_by_type, on="device_type_id", how="outer")
        .fillna({"failure_count": 0})
    )

    # Enforce "MTBF only if > 1 event" at the device-type level
    agg_types.loc[agg_types["failure_count"] <= 1, "MTBF_hours"] = pd.NA

    # -----------------------
    # Device type names
    # -----------------------
    device_types_result = await core.crud.operational.device_types.get_device_types(
        db=project_db_async,
        device_type_ids=agg_types["device_type_id"].unique().tolist(),
    )
    device_types_model_list = ModelList.from_items(list(device_types_result))
    device_types = device_types_model_list.pandas_dataframe(index="device_type_id")

    # -----------------------
    # Build response
    # -----------------------
    metrics: list[EventMetrics] = []
    for _, row in agg_types.iterrows():
        dt_id = int(row["device_type_id"])
        metrics.append(
            EventMetrics(
                device_type_id=dt_id,
                device_type_name=(
                    device_types.loc[dt_id, "name_long"] if dt_id != 5 else "Project"  # type: ignore
                ),
                MTBF_hours=(
                    round(float(row["MTBF_hours"]), 2)
                    if pd.notna(row.get("MTBF_hours"))
                    else None
                ),
                MTTR_hours=(
                    round(float(row["MTTR_hours"]), 2)
                    if pd.notna(row.get("MTTR_hours"))
                    else None
                ),
                failure_count=int(row.get("failure_count", 0)),
                unavailability_contribution=(
                    float(row.get("unavailability_contribution", 0.0))
                    if pd.notna(row.get("unavailability_contribution"))
                    else 0.0
                ),
            )
        )

    return EventMetaData(
        metrics=metrics,
        daily_totals={
            "dates": counts_by_day.index.tolist(),
            "counts": counts_by_day.tolist(),
        },
        device_totals=device_totals,
    )


@router.get("/home-page-summary", response_class=ORJSONResponse)
def get_events_home_page_summary(
    project_db: Session = Depends(get_project_db),
    project: models.Project = Depends(get_project_api),
    sort_by: Literal["daily", "total"] = "daily",
):
    """todo

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
        sort_by: TODO: describe.
    """
    data = core.crud.project.events.get_homepage_summary(
        project_db, project_name=project.name_short, sort_by=sort_by
    )
    return data
