import datetime

from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.enumerations import SensorType, TimeOffset
from sqlalchemy.orm import Session

import core
from core import models


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
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[SensorType.BESS_PCS_AC_POWER],
        deep=True,
    ).models()

    tag_id_to_device_name_long = {t.tag_id: t.device.name_long for t in tags}

    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=[t.tag_id for t in tags],
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.ONE_HOUR,
    ).get()

    df = data.df.to_pandas()
    df = df.set_index("time")
    df.columns = df.columns.astype(int)

    return_data = [
        {
            "x": df.index.tolist(),
            "y": df[c].tolist(),
            "name": tag_id_to_device_name_long[c],
        }
        for c in df.columns.astype(int)
    ]

    # Sort return_data by name
    return_data.sort(key=lambda x: x["name"])

    return return_data
