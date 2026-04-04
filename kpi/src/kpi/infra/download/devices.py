import pandas as pd
from core.crud.project.devices import get_project_devices
from core.db_query import OutputType

from core import models


def download_device_df(
    project_name_short: str, device_type_ids: list[int]
) -> pd.DataFrame:
    devices = get_project_devices(
        device_type_ids=list(device_type_ids),
    ).get(
        schema=project_name_short,
        output_type=OutputType.PANDAS,
    )

    return devices.set_index(models.Device.device_id.name)
