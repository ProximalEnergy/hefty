import datetime

import pandas as pd
from sqlalchemy.orm import Session

import core
from app import utils
from core import models


def get_bess_pcs_data(
    *,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
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
        sensor_type_ids=[31],  # bess_pcs_ac_power
        deep=True,
    ).models()

    tag_id_to_device_name_long = {t.tag_id: t.device.name_long for t in tags}

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
