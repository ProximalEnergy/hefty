import json
import sys
from io import StringIO

import pandas as pd
import psycopg2

from .. import utils

project_name_short = "<project_name_short>"
update_project_spec = True
update_devices = True

# grab arguments from command line
if len(sys.argv) > 1:
    project_name_short = sys.argv[1]
if len(sys.argv) > 2:
    if sys.argv[2] == "True":
        update_project_spec = True
    elif sys.argv[2] == "False":
        update_project_spec = False
    else:
        raise ValueError(f"Invalid value for update_project_spec: {sys.argv[2]}")
if len(sys.argv) > 3:
    if sys.argv[3] == "True":
        update_devices = True
    elif sys.argv[3] == "False":
        update_devices = False
    else:
        raise ValueError(f"Invalid value for update_devices: {sys.argv[3]}")

devices = pd.read_excel(
    utils.EXCEL_PATH / f"{project_name_short}.xlsx",
    sheet_name="devices",
    dtype={"name_short": str, "name_long": str},
)
devices = utils.clean_df(devices, index_col="device_id")
devices = utils.get_device_id_path(devices)

# Identify unique device_type_ids that are used in the project
used_device_type_ids = sorted(devices["device_type_id"].unique().tolist())

# Identify device_type_ids that all have GIS points
device_types_all_with_points = (
    devices.groupby("device_type_id")["point"]
    .apply(lambda x: x.notnull().all())
    .loc[lambda x: x]
    .index.tolist()
)

# Identify device_type_ids that all have GIS polygons
device_types_all_with_polygons = (
    devices.groupby("device_type_id")["polygon"]
    .apply(lambda x: x.notnull().all())
    .loc[lambda x: x]
    .index.tolist()
)

# Query the project.spec for this project
if update_project_spec:
    with psycopg2.connect(
        utils.CONNECTION_STRING,
        application_name=utils.application_name(__file__),
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT spec
                FROM operational.projects
                WHERE name_short = '{project_name_short}'""",
            )
            result = cursor.fetchone()
            if result is None:
                raise ValueError(
                    f"No project found with name_short = '{project_name_short}'",
                )
            project_spec = result[0]

            # Update the project.spec
            project_spec["used_device_type_ids"] = used_device_type_ids
            project_spec["device_types_all_with_points"] = device_types_all_with_points
            project_spec["device_types_all_with_polygons"] = (
                device_types_all_with_polygons
            )

            # Update the project.spec in the database
            cursor.execute(
                f"""
                UPDATE operational.projects
                SET spec = '{json.dumps(project_spec)}'
                WHERE name_short = '{project_name_short}'
                """,
            )

            conn.commit()

# Check for missing columns to ensure backwards compatibility
# (When columns have not been added in Excel yet)
if "logical" not in devices.columns:
    devices["logical"] = False
if "pv_module_id" not in devices.columns:
    devices["pv_module_id"] = None
if "device_model_id" not in devices.columns:
    devices["device_model_id"] = None

if update_devices:
    with psycopg2.connect(
        utils.CONNECTION_STRING,
        application_name=utils.application_name(__file__),
    ) as conn:
        with conn.cursor() as cursor:
            with StringIO() as sio:
                # NOTE: \t used because WKT data contains commas
                sio.write(devices.to_csv(sep="\t", index=False, header=False))
                sio.seek(0)

                cursor.execute(
                    f"""
                    CREATE TEMP TABLE temp_{project_name_short}_devices AS
                    SELECT * FROM {project_name_short}.devices
                    WITH NO DATA;
                    """,
                )

                cursor.copy_from(
                    sio,
                    f"temp_{project_name_short}_devices",
                    columns=devices.columns,
                    sep="\t",
                    null="",
                )

                cursor.execute(
                    f"""
                    INSERT INTO {project_name_short}.devices
                    SELECT * FROM temp_{project_name_short}_devices
                    ON CONFLICT (device_id)
                    DO UPDATE SET
                        device_id_path = EXCLUDED.device_id_path,
                        device_type_id = EXCLUDED.device_type_id,
                        device_model_id = EXCLUDED.device_model_id,
                        cec_pv_inverter_id = EXCLUDED.cec_pv_inverter_id,
                        cec_pv_module_id = EXCLUDED.cec_pv_module_id,
                        pv_module_id = EXCLUDED.pv_module_id,
                        parent_device_id = EXCLUDED.parent_device_id,
                        logical = EXCLUDED.logical,
                        name_short = EXCLUDED.name_short,
                        name_long = EXCLUDED.name_long,
                        capacity_dc = EXCLUDED.capacity_dc,
                        capacity_ac = EXCLUDED.capacity_ac,
                        capacity_energy_dc = EXCLUDED.capacity_energy_dc,
                        point = EXCLUDED.point,
                        polygon = EXCLUDED.polygon;
                    """,
                )

            conn.commit()
