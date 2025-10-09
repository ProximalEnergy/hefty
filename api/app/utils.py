import datetime
import functools
import hashlib
import random
import warnings
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from pvlib import irradiance, location, tracking  # type: ignore
from sqlalchemy.orm import Session

import core
from app import settings
from app._crud.operational.sensor_types import get_sensor_types
from app._crud.projects.data import get_project_data, get_project_data_latest
from app._crud.projects.data_raw import (
    get_project_data_raw,
    get_project_data_raw_last,
    get_project_data_raw_latest,
)
from app._crud.projects.data_timeseries import (
    get_project_data_timeseries,
    get_project_data_timeseries_last,
    get_project_data_timeseries_latest,
)
from core import models

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
    Get whether to include endpoints in the Swagger UI based on the environment. If the `ENVIRONMENT` environment variable is set to "development", return True. Otherwise, return False.

    Returns:
        bool: Whether to include endpoints in the Swagger UI.
    """
    environment = settings.ENVIRONMENT

    if environment == "development":
        return True
    else:
        return False


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
    seed_value = int(hashlib.md5(name.encode()).hexdigest(), 16)
    random.seed(seed_value)


def anonymize_projects(*, projects: list[models.Project]) -> list[models.Project]:
    for project in projects:
        seed_from_project_name(name=project.name_long)
        name = generate_random_name()
        name_short = name.lower().replace(" ", "_")
        name_long = name

        project.name_short = name_short
        project.name_long = name_long

    return projects


def generate_random_name() -> str:
    adjective = random.choice(PROJECT_NAME_ADJECTIVES)
    noun = random.choice(PROJECT_NAME_NOUNS)
    return f"{adjective} {noun}"


def generate_random_location() -> tuple[float, float]:
    latitude = random.uniform(24.396308, 49.384358)
    longitude = random.uniform(-125.000000, -66.934570)
    return latitude, longitude


def generate_random_project(*, name: str) -> tuple[str, float, float]:
    seed_from_project_name(name=name)

    name = generate_random_name()
    latitude, longitude = generate_random_location()

    return name, latitude, longitude


def timedelta_to_postgres_interval(*, timedelta: pd.Timedelta) -> str:
    # Extract the components of the timedelta
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
    if len(db_data) == 0:
        raise HTTPException(status_code=404, detail="No data found")

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
    # NOTE: Context manager required for pandas 3.0 readiness. See the following resources for more information:
    # - https://pandas.pydata.org/docs/whatsnew/v2.2.0.html#deprecated-automatic-downcasting
    # - https://github.com/pandas-dev/pandas/issues/57734
    # - https://medium.com/@felipecaballero/deciphering-the-cryptic-futurewarning-for-fillna-in-pandas-2-01deb4e411a1
    with pd.option_context("future.no_silent_downcasting", True):
        df["value"] = df.filter(regex="value").bfill(axis=1).iloc[:, 0]

    df = df.infer_objects()

    return df


# NOTE: This is the single function that should be called to query time series
# data from the database.
def data_df(
    project_db: Session,
    project: models.Project,
    tags: list[models.Tag],
    *,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    interval: str = "5min",
    agg: str = "instantaneous",
    start_offset: str = "5min",
    get_last: bool = False,
    last_offset: str = "1hour",
    fillna_zero: bool = True,
    ffill_limit: int | None = None,
    unit_scaled: bool = True,
) -> pd.DataFrame:
    """
    Get time series data from the database and return as a DataFrame.

    Args:
        project_db (Session): SQLAlchemy session.
        project (models.Project): Project model.
        tags (List[models.Tag]): List of Tag models.
        start (Optional[datetime.datetime], optional): Start time, inclusive. Defaults to None.
        end (Optional[datetime.datetime], optional): End time, exclusive. Defaults to None.
        interval (str, optional): Interval. Defaults to "5min".
        agg (str, optional): Aggregation function. Defaults to "instantaneous".
        start_offset (str, optional): Start offset. Time prior to `start` to query MQTT data. Defaults to "5min".
        get_last (bool, optional): Get last known data point. Defaults to False.
        last_offset (str, optional): Last offset. Window to search for last known data point. Defaults to "1hour".
        fillna_zero (bool, optional): Fill NaN with 0. Defaults to True.
        ffill_limit (Optional[int], optional): Forward fill limit. Defaults to None.
        unit_scaled (bool, optional): Whether to apply unit scaling to the data. Defaults to True.

    Raises:
        HTTPException: If any of the input parameters are invalid.

    Returns:
        pd.DataFrame: DataFrame with time series data.
    """

    # Check that tags is not empty
    if len(tags) == 0:
        raise HTTPException(status_code=400, detail="No tags specified")

    # Check for valid aggregation functions
    AGG_FUNCTIONS = ["instantaneous"]
    if agg not in AGG_FUNCTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid aggregation."
                f"Supported aggregation functions are {AGG_FUNCTIONS}."
            ),
        )

    # Ensure that last_offset is not too large
    last_offset_max = "1D"
    if pd.Timedelta(last_offset) > pd.Timedelta(last_offset_max):
        raise HTTPException(
            status_code=400,
            detail=f"last_offset must be less than or equal to {last_offset_max}.",
        )

    # If start is None, set to beginning of day
    if start is None:
        start = pd.Timestamp.now(tz=project.time_zone).floor("D")
    else:
        start = pd.Timestamp(start)
        # If start is naive, localize to project time zone
        if start.tzinfo is None:
            start = start.tz_localize(project.time_zone)
        # If start is in different time zone, convert to project time zone
        else:
            start = start.tz_convert(project.time_zone)

    # If end is None, set to end of day
    if end is None:
        end = pd.Timestamp.now(tz=project.time_zone).ceil(interval)
    else:
        end = pd.Timestamp(end)
        # If end is naive, localize to project time zone
        if end.tzinfo is None:
            end = end.tz_localize(project.time_zone)
        # If end is in different time zone, convert to project
        else:
            end = end.tz_convert(project.time_zone)

    # NOTE: Here, we have `start` and `end` as tz-aware timestamps in the
    # project time zone

    # If project has unevenly spaced data, query start_offset before start.
    # This will allow the first requested interval to be populated.
    if project.data_interval == "mqtt":
        start_query = start - pd.Timedelta(start_offset)
    else:
        start_query = start

    # NOTE: This is temporary and can be removed once all projects have data in
    # data_raw table.
    if project.data_interval == "mqtt":
        raw = True
    else:
        raw = False

    tag_ids = [tag.tag_id for tag in tags]

    try:
        time_delta_requested = pd.Timedelta(interval)
        interval_sql = timedelta_to_postgres_interval(timedelta=time_delta_requested)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interval")

    # Ensure the query does not ask for too much data at one time
    MAX_DATA_POINTS = (
        10_000_000  # ~1 days worth of all DBD tracker data at 5 minute intervals
    )
    time_intervals = (end - start) / time_delta_requested
    data_points = time_intervals * len(tags)
    if data_points > MAX_DATA_POINTS:
        raise HTTPException(
            status_code=422,
            detail=f"Query would return more than {MAX_DATA_POINTS:,} data points. Please reduce the time range or the number of tags.",
        )

    date_range_requested = pd.date_range(
        start=start,
        end=end,
        freq=time_delta_requested,
        inclusive="left",
    )
    df_requested_index = pd.DataFrame(index=date_range_requested)

    if project.data_table == "data":
        data = get_project_data(
            db=project_db,
            tag_ids=tag_ids,
            start=start_query,
            end=end,
            raw=raw,
        )
        df = parse_db_data_to_df(db_data=data)

        # Pivot DataFrame so that each tag_id is a column
        df = df.pivot(index="time", columns="tag_id", values="value")
        df = df_requested_index.join(df, how="outer")
    elif project.data_table in ["data_raw", "data_timeseries"]:
        if project.data_table == "data_raw":
            data = get_project_data_raw(
                project_db=project_db,
                project_name_short=project.name_short,
                tag_ids=tag_ids,
                start=start_query,
                end=end,
                interval=interval_sql,
            )
        else:
            data = get_project_data_timeseries(
                project_db,
                project.name_short,
                tag_ids,
                start_query,
                end,
                interval_sql,
                cagg_interval=project.data_cagg_interval,
            )

        df = parse_db_data_to_df(db_data=data)

        # Pivot DataFrame so that each tag_id is a column
        df = df.pivot(index="time", columns="tag_id", values="value")
        df = df_requested_index.join(df, how="outer")

        # Forward fill missing data
        with pd.option_context("future.no_silent_downcasting", True):
            df = df.ffill(limit=ffill_limit)

        df = df.loc[df_requested_index.index]

        if get_last:
            cols_before_reindex = df.columns[df.iloc[0].isna()]
            tag_ids_last_before_reindex = [int(c) for c in cols_before_reindex]

            # Ensure that all expected columns are present
            # NOTE: This is necessary because if a tag has no data in the database, it
            # will not be included in the DataFrame
            df = df.reindex(columns=tag_ids, fill_value=np.nan)

            # Get columns that have NaN in the first row
            cols_after_reindex = df.columns[df.iloc[0].isna()]
            tag_ids_last_after_reindex = [int(c) for c in cols_after_reindex]

            MAX_LAST_TAGS = 1_000
            if len(tag_ids_last_after_reindex) <= MAX_LAST_TAGS:
                tag_ids_last = tag_ids_last_after_reindex
            elif len(tag_ids_last_before_reindex) <= MAX_LAST_TAGS:
                tag_ids_last = tag_ids_last_before_reindex
            else:
                tag_ids_last = None

            if tag_ids_last is not None and len(tag_ids_last) > 0:
                end_last = start
                start_last = end_last - pd.Timedelta(last_offset)

                if project.data_table == "data_raw":
                    data_last = get_project_data_raw_last(
                        project_db=project_db,
                        project_name_short=project.name_short,
                        tag_ids=tag_ids_last,
                        start=start_last,
                        end=end_last,
                    )
                else:
                    data_last = get_project_data_timeseries_last(
                        project_db,
                        project.name_short,
                        tag_ids_last,
                        start_last,
                        end_last,
                        cagg_interval=project.data_cagg_interval,
                    )

                if len(data_last) > 0:
                    df_last = parse_db_data_to_df(db_data=data_last)

                    # Pivot DataFrame so that each tag_id is a column
                    df_last = df_last.pivot(
                        index="time",
                        columns="tag_id",
                        values="value",
                    )
                    df_last.index = pd.to_datetime(df_last.index)

                    df.update(df_last)

                    df = df.ffill(limit=ffill_limit)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid data table",
        )

    # Ensure that all expected columns are present
    # NOTE: This is necessary because if a tag has no data in the database, it
    # will not be included in the DataFrame
    df = df.reindex(columns=tag_ids, fill_value=np.nan)

    if fillna_zero:
        with pd.option_context("future.no_silent_downcasting", True):
            df = df.fillna(0)

    # Convert data to correct units
    if unit_scaled:
        for tag in tags:
            if tag.unit_scale is not None:
                df[tag.tag_id] = df[tag.tag_id] * tag.unit_scale
            if tag.unit_offset is not None:
                df[tag.tag_id] = df[tag.tag_id] + tag.unit_offset

    # Make sure that any data after right now is null and not forward filled
    df.loc[df.index > pd.Timestamp.utcnow()] = np.nan

    return df


def data_latest_df(
    project_db: Session,
    project: models.Project,
    tags: list[models.Tag],
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


def get_tag_id_to_tag_name(
    db: Session,
    *,
    tags: list[models.Tag],
) -> dict[int, str]:
    # Get list of unique sensor type ids
    sensor_type_ids = list(set([tag.sensor_type_id for tag in tags]))

    # Get list of sensor types
    sensor_types = get_sensor_types(db, sensor_type_ids=sensor_type_ids)  # type: ignore

    # Create mapping from sensor type id to sensor type name
    sensor_type_id_to_name_metric = {
        sensor_type.sensor_type_id: sensor_type.name_metric
        for sensor_type in sensor_types
    }

    # Create mapping from tag id to sensor type name metric
    tag_id_to_name_metric = {
        tag.tag_id: sensor_type_id_to_name_metric[tag.sensor_type_id] for tag in tags
    }

    return tag_id_to_name_metric


def get_tag_id_to_sensor_type_name(
    db: Session,
    *,
    tags: list[models.Tag],
) -> dict[int, str]:
    # Get list of unique sensor type ids
    sensor_type_ids = list(set([tag.sensor_type_id for tag in tags]))

    # Get list of sensor types
    sensor_types = get_sensor_types(db, sensor_type_ids=sensor_type_ids)  # type: ignore

    # Create mapping from sensor type id to sensor type name
    sensor_type_id_to_name_short = {
        sensor_type.sensor_type_id: sensor_type.name_short
        for sensor_type in sensor_types
    }

    # Create mapping from tag id to sensor type name metric
    tag_id_to_name_short = {
        tag.tag_id: sensor_type_id_to_name_short[tag.sensor_type_id] for tag in tags
    }

    return tag_id_to_name_short


def get_tag_id_to_device_name_long(
    db: Session,
    *,
    tags: list[models.Tag],
) -> dict[int, str]:
    # Get list of unique device ids
    device_ids = list(set([tag.device_id for tag in tags]))

    # Get list of devices
    devices = core.crud.project.devices.get_project_devices(
        db,
        device_ids=device_ids,
        device_type_ids=[],
        parent_device_ids=[],
        name_short="",
        name_long="",
        deep=False,
    ).models()

    # Create mapping from device id to device name long
    device_id_to_name_long = {
        device.device_id: device.name_long if device.name_long else ""
        for device in devices
    }

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
    """
    Calculate the tracking angles for a solar tracker based on the site location and specified parameters.

    Args:
        site_location (location.Location): The geographical location of the site.
        start_date (datetime.datetime): The start date and time for the calculation.
        end_date (datetime.datetime): The end date and time for the calculation.
        freq (str, optional): The frequency of the time intervals. Defaults to "5min".
        axis_tilt (float, optional): The tilt angle of the tracking axis. Defaults to 0.
        axis_azimuth (float, optional): The azimuth angle of the tracking axis. Defaults to 180.
        max_angle (float, optional): The maximum angle the tracker can tilt. Defaults to 60.
        backtrack (bool, optional): Whether to enable backtracking. Defaults to False.
        gcr (float, optional): Ground coverage ratio. Defaults to 0.5.

    Returns:
        pd.DataFrame: A DataFrame containing the tracking angles and surface azimuth for the specified time range.
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
        apparent_azimuth=solpos["azimuth"],
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
    """
    Calculate the plane of array (POA) irradiance for a solar panel based on the site location, date, tilt, and surface azimuth.

    Args:
        site_location (location.Location): The geographical location of the solar panel.
        date (datetime.datetime): The date for which to calculate the irradiance.
        tilt (float): The tilt angle of the solar panel.
        surface_azimuth (float): The azimuth angle of the solar panel.

    Returns:
        pd.DataFrame: A DataFrame containing the global horizontal irradiance (GHI) and the plane of array (POA) irradiance.
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


def deprecated(reason):
    """
    This decorator can be used to mark functions as deprecated.
    It will result in a warning being emitted when the function is used.

    :param reason: A message indicating why the function is deprecated.
    """

    def decorator(func):
        @functools.wraps(func)
        def new_func(*args: str, **kwargs):
            warnings.warn(
                f"Call to deprecated function {func.__name__}. {reason}",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return new_func

    return decorator


def map_ancestors_to_descendents(
    *,
    ancestors: list[models.Device],
    descendents: list[models.Device],
) -> dict[int, list[int]]:
    """
    Map ancestor device ids to a list of descendent device ids.
    """
    # Get all ancestor device_ids
    ids_ancestors = {a.device_id for a in ancestors}

    mapping = defaultdict(list)

    # For each descendent device...
    for d in descendents:
        # Ensure the descendent device has a device_id_path
        if d.device_id_path is None:
            raise ValueError(f"Device {d.device_id} has no device_id_path")

        # Get the device_id_path as a list of strings
        device_id_path = d.device_id_path.split(".")

        # For each ancestor device_id...
        for id in ids_ancestors:
            # If the ancestor device_id is in the descendent device_id_path, add the descendent device_id to the mapping
            if str(id) in device_id_path:
                mapping[id].append(d.device_id)

                # Break out of the loop because we have found the mapping
                break

    return mapping


def kpi_data_list_to_dict(*, kpi_data: list[dict], key: str) -> dict:
    """
    Convert a list of KPI data dictionaries into a dictionary indexed by a specified key.

    This function takes a list of dictionaries containing KPI data and transforms it into a
    dictionary where each entry is keyed by the specified key ('project_id' or 'kpi_type_id').
    Each value in the resulting dictionary is the original KPI data dictionary.

    Args:
        kpi_data (list[dict]): A list of dictionaries containing KPI data.
        key (str): The key to index the resulting dictionary. Must be either 'project_id' or 'kpi_type_id'.

    Raises:
        ValueError: If the provided key is not 'project_id' or 'kpi_type_id'.

    Returns:
        dict: A dictionary where each key is the specified key from the KPI data and each value is the corresponding KPI data dictionary.
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
        kpi_data (dict): A dictionary containing KPI data. It must have the following structure:
            - "data": A dictionary containing:
                - "device_data_obj": A dictionary containing:
                    - "device_values": A list of device values to be used as the DataFrame data.
                - "dates": A list of dates to be used as the DataFrame index.

    Returns:
        pd.DataFrame: A DataFrame where the rows correspond to device values and the index
        corresponds to the dates from the KPI data.
    """
    df = pd.DataFrame(
        kpi_data["data"]["device_data_obj"]["device_values"],
        index=kpi_data["data"]["dates"],
    )

    df = df.astype(float)

    return df
