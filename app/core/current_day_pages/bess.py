import datetime
from collections import defaultdict

import pandas as pd
from sqlalchemy.orm import Session

import core
from app import utils
from core import models


def get_bess_data(
    *,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """
    Retrieves BESS data for a given project.

    Args:
        project: The project model.
        project_db: The project database session.
        start: The start datetime for the data query.
        end: The end datetime for the data query.

    Returns:
        A dictionary containing BESS data.
    """
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[
            43,  # bess_enclosure_soc_percent
            44,  # bess_bank_soc_percent
            45,  # bess_string_soc_percent
        ],
        deep=True,
    ).models()

    tag_id_to_device_name_long = {t.tag_id: t.device.name_long for t in tags}
    sensor_type_id_to_tag_ids = defaultdict(list)
    for t in tags:
        sensor_type_id_to_tag_ids[t.sensor_type_id].append(t.tag_id)

    df = utils.data_df(
        project_db,
        project,
        tags,
        start=start,
        end=end,
        get_last=True,
        fillna_zero=False,
    )
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)

    return_data = {}

    sensor_type_id_to_name = {
        43: "bess_enclosure",
        44: "bess_bank",
        45: "bess_string",
    }

    for sensor_type_id, tag_ids in sensor_type_id_to_tag_ids.items():
        if sensor_type_id:
            return_data[sensor_type_id_to_name[sensor_type_id]] = [
                {
                    "x": df.index.tolist(),
                    "y": df[tag_id].tolist(),
                    "name": tag_id_to_device_name_long[tag_id],
                }
                for tag_id in tag_ids
            ]
            return_data[sensor_type_id_to_name[sensor_type_id]].sort(
                key=lambda x: x["name"],
            )

    return return_data
