import sys
from io import StringIO

import pandas as pd
import psycopg2

from .. import utils

project_name_short = "<project_name_short>"

# grab project name from command line
if len(sys.argv) > 1:
    project_name_short = sys.argv[1]

cmms_devices = pd.read_excel(
    utils.EXCEL_PATH / f"{project_name_short}.xlsx",
    sheet_name="cmms_devices",
)
cmms_devices = utils.clean_df(cmms_devices)

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        with StringIO() as sio:
            # NOTE: \t used because WKT data contains commas
            sio.write(cmms_devices.to_csv(sep="\t", index=False, header=False))
            sio.seek(0)

            cursor.execute(
                f"""
                CREATE TEMP TABLE temp_{project_name_short}_cmms_devices AS
                SELECT * FROM {project_name_short}.cmms_devices
                WITH NO DATA;
                """,
            )

            cursor.copy_from(
                sio,
                f"temp_{project_name_short}_cmms_devices",
                columns=cmms_devices.columns,
                sep="\t",
                null="",
            )

            cursor.execute(
                f"""
                INSERT INTO {project_name_short}.cmms_devices
                SELECT * FROM temp_{project_name_short}_cmms_devices
                ON CONFLICT (cmms_integration_id, cmms_device_id, device_id)
                DO NOTHING
                """,
            )

        conn.commit()
