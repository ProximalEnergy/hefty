import datetime
import hashlib
import random
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Protocol, cast

import numpy as np
import pandas as pd
from core.crud.operational.sensor_types import get_sensor_types
from core.db_query import OutputType
from fastapi import HTTPException
from pvlib import irradiance, location, tracking
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import settings
from app._crud.projects.data import get_project_data_latest
from app._crud.projects.data_raw import (
    get_project_data_raw_latest,
)
from app._crud.projects.data_timeseries import (
    get_project_data_timeseries_latest,
)
from core import models

# EEM nighttime expected-power: project PV inverter capacity_ac (MW) times this
# factor (~0.18% nameplate) yields standby loss MW.
NIGHTTIME_LOSS_FACTOR = -0.0018


class TagLike(Protocol):
    """Tag-like structure used by metadata helpers."""

    tag_id: int
    sensor_type_id: int | None
    device_id: int
    name_scada: str
    name_long: str | None
    unit_scale: float | None


PROJECT_NAME_ADJECTIVES = [
    "Green",
    "Eco",
    "Renewable",
    "Clean",
    "Sustainable",
]

PROJECT_NAME_NOUNS = [
    "Energy Farm",
    "Energy Park",
    "Energy Plant",
    "Energy Station",
    "Power Farm",
    "Power Park",
    "Power Plant",
    "Power Station",
]


def get_include_in_schema() -> bool:
    """
    Get whether to include endpoints in the Swagger UI based on the environment.

    If the `ENVIRONMENT` environment variable is set to "development", return
    True. Otherwise, return False.

    Returns:
        bool: Whether to include endpoints in the Swagger UI.
    """
    environment = settings.ENVIRONMENT

    if environment == "development":
        return True
    else:
        return False


def get_project_schema(*, project_db: Session) -> str | None:
    """Return the project schema name from a project-scoped session."""
    schema_translate_map = (
        project_db.get_bind().get_execution_options().get("schema_translate_map", {})
    )
    return schema_translate_map.get("project")  # type: ignore


async def get_project_schema_async(*, project_db: AsyncSession) -> str | None:
    """Return the project schema name from a project-scoped session (async)."""
    schema_translate_map = (
        project_db.get_bind().get_execution_options().get("schema_translate_map", {})
    )
    return schema_translate_map.get("project")  # type: ignore


def check_404(*, value: Any, detail: Any = None):
    """Raise HTTPException if value is None.

    Args:
        value (Any): Object to check.
        detail (Any, optional): Passed to HTTPException. Defaults to None.

    Raises:
        HTTPException: If value is None.
    """
    if value is None:
        raise HTTPException(status_code=404, detail=detail)


def seed_from_project_name(*, name: str) -> None:
    """Handle seed from project name.

    Args:
        name: Project name used to seed the random generator.
    """
    seed_value = int(hashlib.md5(name.encode()).hexdigest(), 16)
    random.seed(seed_value)


def anonymize_projects(
    *,
    projects: list[models.Project | dict[str, Any]],
) -> list[models.Project | dict[str, Any]]:
    """Handle anonymize projects.

    Args:
        projects: Projects or dicts to anonymize in place.
    """
    for project in projects:
        if isinstance(project, dict):
            name_long = project.get("name_long")
            if not name_long:
                continue
            seed_from_project_name(name=name_long)
            name = generate_random_name()
            name_short = name.lower().replace(" ", "_")
            project["name_short"] = name_short
            project["name_long"] = name
            continue

        seed_from_project_name(name=project.name_long)
        name = generate_random_name()
        name_short = name.lower().replace(" ", "_")
        name_long = name

        project.name_short = name_short
        project.name_long = name_long

    return projects


def generate_random_name() -> str:
    """Handle generate random name."""
    adjective = random.choice(PROJECT_NAME_ADJECTIVES)
    noun = random.choice(PROJECT_NAME_NOUNS)
    return f"{adjective} {noun}"


def generate_random_location() -> tuple[float, float]:
    """Handle generate random location."""
    latitude = random.uniform(24.396308, 49.384358)
    longitude = random.uniform(-125.000000, -66.934570)
    return latitude, longitude


def timedelta_to_postgres_interval(*, timedelta: pd.Timedelta) -> str:
    # Extract the components of the timedelta
    """Handle timedelta to postgres interval.

    Args:
        timedelta: Pandas timedelta to convert into a PostgreSQL interval string.
    """
    days = timedelta.days
    seconds = timedelta.seconds
    microseconds = timedelta.microseconds

    # Construct the PostgreSQL interval parts
    parts = []
    if days > 0:
        parts.append(f"{days} days")
    if seconds > 0:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0:
            parts.append(f"{hours} hours")
        if minutes > 0:
            parts.append(f"{minutes} minutes")
        if seconds > 0:
            parts.append(f"{seconds} seconds")
    if microseconds > 0:
        parts.append(f"{microseconds} microseconds")

    # Join the parts to form the PostgreSQL interval string
    return " ".join(parts)


def parse_db_data_to_df(*, db_data):
    """Handle parse db data to df.

    Args:
        db_data: Query results or dicts used to build the DataFrame.
    """
    if len(db_data) == 0:
        # Return an empty DataFrame with the expected columns so callers can
        # continue gracefully. Previously this function raised a 404, but we
        # now return an empty payload instead of surfacing an error.
        return pd.DataFrame(columns=["time", "tag_id", "value"])

    # Parse database records into DataFrame
    try:
        df = pd.DataFrame.from_records([d.__dict__ for d in db_data])
    except AttributeError:
        df = pd.DataFrame(db_data)
        df = df.rename(columns={"time_bucket": "time"})

    # Ensure correct data types
    if "value_cumulative" in df.columns:
        df["value_cumulative"] = df["value_cumulative"].astype("Int64")
    if "value_status" in df.columns:
        df["value_status"] = df["value_status"].astype("Int32")

    # Collapse value columns into single column (each tag_id only has data of
    # one value type)
    # NOTE: Context manager required for pandas 3.0 readiness. See the
    # following resources for more information:
    # - https://pandas.pydata.org/docs/whatsnew/v2.2.0.html#
    #   deprecated-automatic-downcasting
    # - https://github.com/pandas-dev/pandas/issues/57734
    # - https://medium.com/@felipecaballero/
    #   deciphering-the-cryptic-futurewarning-for-fillna-in-pandas-2-01deb4e411a1
    with pd.option_context("future.no_silent_downcasting", True):
        df["value"] = df.filter(regex="value").bfill(axis=1).iloc[:, 0]

    df = df.infer_objects()

    return df


def data_latest_df(
    project_db: Session,
    project: models.Project,
    tags: Sequence[TagLike],
    *,
    start: datetime.datetime | None = None,
) -> pd.DataFrame:
    """
    Retrieve the most recent time series data for specified tags from the database.

    This function queries the database for the latest data associated with the
    provided tags within a specified time range. If a start time is not provided,
    it defaults to 15 minutes before the current time. The function raises an
    HTTPException if the start time is too far in the past or if the project data
    table is invalid.

    Args:
        project_db (Session): The database session to use for executing the query.
        project (models.Project): The project from which to retrieve the data.
        tags (List[models.Tag]): The list of tags for which to retrieve the data.
        start (Optional[datetime.datetime], optional): The start time for the query.
            Defaults to None, which sets the start time to 15 minutes before now.

    Returns:
        pd.DataFrame: A DataFrame containing the latest data for the specified tags,
        with columns for time, tag_id, and value.
    """
    # todo: unit_offset is not applied in this function
    MAX_START_DELTA = datetime.timedelta(days=1)
    DEFAULT_START_DELTA = datetime.timedelta(minutes=15)

    now = datetime.datetime.now()

    # If start is provided, check that it is not too far in the past
    if start is not None:
        if start < now - MAX_START_DELTA:
            raise HTTPException(
                status_code=400,
                detail="Start time is too far in the past",
            )
    # If start is not provided, set to default
    else:
        start = now - DEFAULT_START_DELTA

    tag_ids = [tag.tag_id for tag in tags]

    if project.data_table == "data":
        data = get_project_data_latest(
            project_db=project_db,
            project_name_short=project.name_short,
            tag_ids=tag_ids,
            start=start,
        )
    elif project.data_table == "data_raw":
        data = get_project_data_raw_latest(
            project_db=project_db,
            project_name_short=project.name_short,
            tag_ids=tag_ids,
            start=start,
        )
    elif project.data_table == "data_timeseries":
        data = get_project_data_timeseries_latest(
            project_db,
            project.name_short,
            tag_ids,
            start,
            cagg_interval=project.data_cagg_interval,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid data table",
        )

    df = parse_db_data_to_df(db_data=data)
    df = df.reset_index()[["time", "tag_id", "value"]]

    tag_ids_with_data = set(df["tag_id"].unique().tolist())
    tag_ids_without_data = set(tag_ids) - tag_ids_with_data

    # Apply unit conversions
    for tag in tags:
        if tag.unit_scale is not None and tag.tag_id in tag_ids_with_data:
            df.loc[df["tag_id"] == tag.tag_id, "value"] = (
                df.loc[df["tag_id"] == tag.tag_id, "value"] * tag.unit_scale
            )

    # If any tags have no data, add them to the DataFrame with NaN values
    if len(tag_ids_without_data) > 0:
        df_missing = pd.DataFrame(
            {
                "time": pd.NaT,
                "tag_id": tag_ids_without_data,
                "value": np.nan,
            },
        )
    df = pd.concat([df, df_missing], ignore_index=True)

    # Sort by tag_id
    df = df.sort_values(by="tag_id", ignore_index=True)

    return df


async def get_tag_id_to_tag_name(
    *,
    tags: Sequence[TagLike],
) -> dict[int, str]:
    # Get list of unique sensor type ids
    """Get tag id to tag name.

    Args:
        tags: Tag-like records to map to sensor type names.
    """
    sensor_type_ids = list(
        {tag.sensor_type_id for tag in tags if tag.sensor_type_id is not None}
    )

    if not sensor_type_ids:
        return {tag.tag_id: "" for tag in tags}

    # Get list of sensor types
    sensor_types = await get_sensor_types(
        sensor_type_ids=sensor_type_ids,
    ).get_async(output_type=OutputType.PANDAS)

    # Create mapping from sensor type id to sensor type name
    sensor_type_id_to_name_metric = dict(
        zip(sensor_types["sensor_type_id"], sensor_types["name_metric"])
    )

    # Create mapping from tag id to sensor type name metric
    tag_id_to_name_metric: dict[int, str] = {}
    for tag in tags:
        sensor_type_id = tag.sensor_type_id
        if sensor_type_id is None:
            tag_id_to_name_metric[tag.tag_id] = ""
            continue

        tag_id_to_name_metric[tag.tag_id] = sensor_type_id_to_name_metric.get(
            sensor_type_id, ""
        )

    return tag_id_to_name_metric


async def get_tag_id_to_sensor_type_name(
    *,
    tags: Sequence[TagLike],
) -> dict[int, str]:
    # Get list of unique sensor type ids
    """Get tag id to sensor type name.

    Args:
        tags: Tag-like records to map to sensor type short names.
    """
    sensor_type_ids = list(
        {tag.sensor_type_id for tag in tags if tag.sensor_type_id is not None}
    )

    if not sensor_type_ids:
        return {tag.tag_id: "" for tag in tags}

    # Get list of sensor types
    sensor_types = await get_sensor_types(
        sensor_type_ids=sensor_type_ids,
    ).get_async(output_type=OutputType.PANDAS)

    # Create mapping from sensor type id to sensor type name
    sensor_type_id_to_name_short = dict(
        zip(sensor_types["sensor_type_id"], sensor_types["name_short"])
    )

    # Create mapping from tag id to sensor type name metric
    tag_id_to_name_short: dict[int, str] = {}
    for tag in tags:
        sensor_type_id = tag.sensor_type_id
        if sensor_type_id is None:
            tag_id_to_name_short[tag.tag_id] = ""
            continue

        tag_id_to_name_short[tag.tag_id] = sensor_type_id_to_name_short.get(
            sensor_type_id, ""
        )

    return tag_id_to_name_short


async def get_tag_id_to_device_name_long(
    db: Session,
    *,
    tags: Sequence[TagLike],
) -> dict[int, str]:
    # Get list of unique device ids
    """Get tag id to device name long.

    Args:
        db: SQLAlchemy session for the project database.
        tags: Tag-like records to map to device names.
    """
    device_ids = list(set([tag.device_id for tag in tags]))

    # Get list of devices
    project_schema = get_project_schema(project_db=db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Create mapping from device id to device name long
    name_long_series = devices_df["name_long"].fillna("")
    device_id_to_name_long = dict(
        zip(devices_df["device_id"].astype(int), name_long_series)
    )

    # Create mapping from tag id to device name long
    tag_id_to_name_long = {
        tag.tag_id: device_id_to_name_long[tag.device_id] for tag in tags
    }

    return tag_id_to_name_long


def get_tracking_angles(
    *,
    site_location: location.Location,
    start: datetime.datetime,
    end: datetime.datetime,
    freq: str = "5min",
    axis_tilt: float = 0,
    axis_azimuth: float = 180,
    max_angle: float = 60,
    backtrack: bool = False,
    gcr: float = 0.5,
) -> pd.DataFrame:
    """Compute tracking angles for a site and time range.

    Args:
        site_location: PVLib location describing the site.
        start: Range start (timezone-aware).
        end: Range end (timezone-aware).
        freq: Pandas frequency string for the output.
        axis_tilt: Tracker axis tilt angle in degrees.
        axis_azimuth: Tracker axis azimuth in degrees.
        max_angle: Maximum tracker rotation angle in degrees.
        backtrack: Whether to use backtracking.
        gcr: Ground coverage ratio for backtracking.
    """
    # Create date range
    times = pd.date_range(
        start=start,
        end=end,
        freq=freq,
        tz=site_location.tz,
        inclusive="left",
    )

    # Get solar position data
    solpos = site_location.get_solarposition(times)

    # Get tracking data
    tracking_df = tracking.singleaxis(
        apparent_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        axis_tilt=axis_tilt,
        axis_azimuth=axis_azimuth,
        max_angle=max_angle,
        backtrack=backtrack,
        gcr=gcr,
    )
    tracking_df["tracker_theta"] = tracking_df["tracker_theta"].fillna(0)
    tracking_df["surface_azimuth"] = tracking_df["surface_azimuth"].fillna(0)

    return pd.DataFrame(tracking_df)


def get_truetracking_irradiance(
    *,
    site_location: location.Location,
    start: datetime.datetime,
    end: datetime.datetime,
    tilt: pd.Series,
    surface_azimuth: pd.Series,
) -> pd.DataFrame:
    """Compute clearsky and plane-of-array irradiance for tracking.

    Args:
        site_location: PVLib location describing the site.
        start: Range start (timezone-aware).
        end: Range end (timezone-aware).
        tilt: Surface tilt series used for irradiance.
        surface_azimuth: Surface azimuth series used for irradiance.
    """
    # Create date range
    times = pd.date_range(
        start=start,
        end=end,
        freq="5min",
        tz=site_location.tz,
        inclusive="left",
    )

    # Get clearsky data
    clearsky = site_location.get_clearsky(times)

    # Get solar position data
    solar_position = site_location.get_solarposition(times=times)

    # Get irradiance data
    poa_irradiance = irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=surface_azimuth,
        dni=clearsky["dni"],
        ghi=clearsky["ghi"],
        dhi=clearsky["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
    )

    result = pd.concat(
        [
            clearsky[["ghi"]],
            poa_irradiance[["poa_global"]],
        ],
        axis=1,
    )
    return pd.DataFrame(result)


def night_mask_leq_horizon(
    *,
    project: models.Project,
    index: pd.DatetimeIndex,
) -> pd.Series:
    """True where the solar elevation is at or below the horizon.

    Args:
        project: Project with geography point and IANA time zone.
        index: Timezone-aware datetimes for the frame to classify.

    Returns:
        Boolean series aligned to ``index``.
    """
    lon, lat = project.point.coordinates  # type: ignore[attr-defined]
    site = location.Location(lat, lon, tz=project.time_zone)
    solpos = site.get_solarposition(times=index)
    elevation = solpos["elevation"]
    return cast(pd.Series, elevation <= 0)


def map_ancestors_to_descendents(
    *,
    ancestors: list[models.Device] | pd.DataFrame,
    descendents: list[models.Device] | pd.DataFrame,
) -> dict[int, list[int]]:
    """Map ancestor device ids to a list of descendent device ids.

    Args:
        ancestors: Ancestor devices or DataFrame of ancestor ids.
        descendents: Descendent devices or DataFrame with device paths.
    """
    if isinstance(ancestors, pd.DataFrame):
        ids_ancestors = set(ancestors["device_id"].dropna().astype(int).tolist())
    else:
        ids_ancestors = {a.device_id for a in ancestors}

    mapping = defaultdict(list)

    if isinstance(descendents, pd.DataFrame):
        for _, row in descendents.iterrows():
            device_id_path = row.get("device_id_path")
            if device_id_path is None:
                raise ValueError(f"Device {row.get('device_id')} has no device_id_path")

            device_id = int(row["device_id"])
            path_parts = str(device_id_path).split(".")
            for ancestor_id in ids_ancestors:
                if str(ancestor_id) in path_parts:
                    mapping[ancestor_id].append(device_id)
                    break
    else:
        # For each descendent device...
        for d in descendents:
            # Ensure the descendent device has a device_id_path
            if d.device_id_path is None:
                raise ValueError(f"Device {d.device_id} has no device_id_path")

            # Get the device_id_path as a list of strings
            device_id_path = d.device_id_path.split(".")

            # For each ancestor device_id...
            for ancestor_id in ids_ancestors:
                # If the ancestor device_id is in the descendent device_id_path,
                # add the descendent device_id to the mapping
                if str(ancestor_id) in device_id_path:
                    mapping[ancestor_id].append(d.device_id)

                    # Break out of the loop because we have found the mapping
                    break

    return mapping


def kpi_data_list_to_dict(*, kpi_data: list[dict], key: str) -> dict:
    """
    Convert a list of KPI data dictionaries into a dictionary indexed by a key.

    This function takes a list of dictionaries containing KPI data and
    transforms it into a dictionary where each entry is keyed by the specified
    key ('project_id' or 'kpi_type_id'). Each value in the resulting dictionary
    is the original KPI data dictionary.

    Args:
        kpi_data (list[dict]): A list of dictionaries containing KPI data.
        key (str): The key to index the resulting dictionary. Must be either
            'project_id' or 'kpi_type_id'.

    Raises:
        ValueError: If the provided key is not 'project_id' or 'kpi_type_id'.

    Returns:
        dict: A dictionary where each key is the specified key from the KPI
            data and each value is the corresponding KPI data dictionary.
    """
    if key not in ["project_id", "kpi_type_id"]:
        raise ValueError("Key must be either 'project_id' or 'kpi_type_id'")

    return {kpi[key]: kpi for kpi in kpi_data}


def parse_kpi_data_to_df(
    *,
    kpi_data: dict,
) -> pd.DataFrame:
    """
    Convert KPI data into a Pandas DataFrame.

    This function takes a dictionary containing KPI data and transforms it into a
    Pandas DataFrame. The DataFrame is constructed using the device values and
    dates from the provided KPI data. Note that this will drop any additional data
    in the KPI data dictionary.

    Args:
        kpi_data (dict): A dictionary containing KPI data. It must have the
            following structure:
            - "data": A dictionary containing:
                - "device_data_obj": A dictionary containing:
                    - "device_values": A list of device values to be used as
                      the DataFrame data.
                - "dates": A list of dates to be used as the DataFrame index.

    Returns:
        pd.DataFrame: A DataFrame where the rows correspond to device values
        and the index corresponds to the dates from the KPI data.
    """
    df = pd.DataFrame(
        kpi_data["data"]["device_data_obj"]["device_values"],
        index=kpi_data["data"]["dates"],
    )

    df = df.astype(float)

    return df
