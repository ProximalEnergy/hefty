import datetime

from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import SensorTypeEnum, TimeOffset
from sqlalchemy.orm import Session

from app import utils
from core import crud, models


async def get_bess_pcs_data(
    *,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """
    Retrieves BESS PCS data for a given project.

    Args:
        project: The project model.
        project_db: The project database session.
        start: The start datetime for the data query.
        end: The end datetime for the data query.

    Returns:
        A list of dictionaries containing BESS PCS data.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    tags_df = await crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorTypeEnum.BESS_PCS_AC_POWER],
        deep=True,
    ).get_async(output_type=OutputType.POLARS, schema=project_schema)

    if tags_df.is_empty():
        return []

    tag_id_to_device_name_long = {
        int(tid): name
        for tid, name in zip(
            tags_df["tag_id"],
            tags_df["device_name_long"].fill_null(""),
            strict=True,
        )
        if tid is not None
    }

    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_df,
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.ONE_HOUR,
    ).get()

    df_dict = data.df.to_dict(as_series=False)
    time_series = df_dict.pop("time")
    return_data = [
        {
            "x": time_series,
            "y": values,
            "name": tag_id_to_device_name_long.get(int(tag_id), ""),
        }
        for tag_id, values in df_dict.items()
        if tag_id is not None
    ]

    # Sort return_data by name
    return_data.sort(key=lambda x: x["name"])

    return return_data
