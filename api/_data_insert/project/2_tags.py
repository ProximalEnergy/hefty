import json
import logging
import sys
from io import StringIO

import pandas as pd
import psycopg2

from .. import utils

project_name_short = "<project_name_short>"
update_project_spec = True
update_tags = True

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
        update_tags = True
    elif sys.argv[3] == "False":
        update_tags = False
    else:
        raise ValueError(f"Invalid value for update_tags: {sys.argv[3]}")

tags = pd.read_excel(
    utils.EXCEL_PATH / f"{project_name_short}.xlsx",
    sheet_name="tags",
    dtype={"name_short": str, "name_long": str},
)

sensor_type_ids = sorted(tags["sensor_type_id"].dropna().astype(int).unique().tolist())

if update_project_spec:
    # Query the project.spec for this project
    with psycopg2.connect(
        utils.CONNECTION_STRING,
        application_name=utils.application_name(__file__),
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT spec FROM operational.projects WHERE name_short = '{project_name_short}'",
            )
            result = cursor.fetchone()
            if result is None:
                raise ValueError(
                    f"No project found with name_short = '{project_name_short}'",
                )
            project_spec = result[0]

            # Update the project.spec with the new sensor_type_ids
            project_spec["used_sensor_type_ids"] = sensor_type_ids

            # Update the project.spec in the database
            cursor.execute(
                f"UPDATE operational.projects SET spec = '{json.dumps(project_spec)}' WHERE name_short = '{project_name_short}'",
            )

            conn.commit()

# If "pg_data_type_id" column does not exist, add it and set all values to 0
# NOTE: This is to handle projects where this column was not created yet in Excel
if "pg_data_type_id" not in tags.columns:
    tags["pg_data_type_id"] = 0

# If "status_lookup_id" column does not exist, add it and set all values to None
# NOTE: This is to handle projects where this column was not created yet in Excel
if "status_lookup_id" not in tags.columns:
    tags["status_lookup_id"] = None

# If "_to_delete" column does not exist, add it and set all values to False
# NOTE: This is to handle projects where this column was not created yet in Excel
# This has to be done before cleaning because all columns starting with "_" are ignored
if "_to_delete" not in tags.columns:
    tags["_to_delete"] = False

# Get a list of tag_ids that are to be deleted
tag_ids_to_delete = tags[tags["_to_delete"]]["tag_id"].astype(int).tolist()

# Include only tags that are not to be deleted
tags = tags[~tags["_to_delete"]]

# Clean the DataFrame
tags = utils.clean_df(tags, index_col="tag_id")

CHUNK_SIZE = 50000  # Number of tags to process per chunk


def process_tag_chunk(tag_chunk):
    with psycopg2.connect(
        utils.CONNECTION_STRING,
        application_name=utils.application_name(__file__),
    ) as conn:
        with conn.cursor() as cursor:
            with StringIO() as sio:
                # NOTE: \t used because WKT data contains commas
                sio.write(tag_chunk.to_csv(sep="\t", index=False, header=False))
                sio.seek(0)

                cursor.execute(
                    f"""
                    CREATE TEMP TABLE temp_{project_name_short}_tags AS
                    SELECT * FROM {project_name_short}.tags
                    WITH NO DATA;
                    """,
                )

                cursor.copy_from(
                    sio,
                    f"temp_{project_name_short}_tags",
                    columns=tag_chunk.columns,
                    sep="\t",
                    null="",
                )

                logging.info("Inserting/updating tags")
                cursor.execute(
                    f"""
                    INSERT INTO {project_name_short}.tags
                    SELECT * FROM temp_{project_name_short}_tags
                    ON CONFLICT (tag_id)
                    DO UPDATE SET
                        device_id = EXCLUDED.device_id,
                        in_tsdb = EXCLUDED.in_tsdb,
                        sensor_type_id = EXCLUDED.sensor_type_id,
                        pg_data_type_id = EXCLUDED.pg_data_type_id,
                        data_type_id = EXCLUDED.data_type_id,
                        name_short = EXCLUDED.name_short,
                        name_long = EXCLUDED.name_long,
                        name_scada = EXCLUDED.name_scada,
                        scada_id = EXCLUDED.scada_id,
                        scada_type = EXCLUDED.scada_type,
                        unit_scada = EXCLUDED.unit_scada,
                        unit_offset = EXCLUDED.unit_offset,
                        unit_scale = EXCLUDED.unit_scale,
                        point = EXCLUDED.point,
                        polygon = EXCLUDED.polygon,
                        status_lookup_id = EXCLUDED.status_lookup_id;
                    """,
                )

                conn.commit()


if update_tags:
    # Process tags in chunks of CHUNK_SIZE
    for start in range(0, len(tags), CHUNK_SIZE):
        end = start + CHUNK_SIZE
        tag_chunk = tags.iloc[start:end]
        logging.info(
            f"Processing tag chunk {start // CHUNK_SIZE + 1} of {(len(tags) - 1) // CHUNK_SIZE + 1}"
        )
        process_tag_chunk(tag_chunk)

    # Delete tags that are to be deleted, chunked by 1000
    with psycopg2.connect(
        utils.CONNECTION_STRING,
        application_name=utils.application_name(__file__),
    ) as conn:
        with conn.cursor() as cursor:
            for i in range(0, len(tag_ids_to_delete), 1000):
                logging.info(
                    f"Deleting chunk {(i // 1000) + 1} of {(len(tag_ids_to_delete) // 1000) + 1}",
                )
                chunk = tag_ids_to_delete[i : i + 1000]

                cursor.execute(
                    f"""
                    DELETE FROM {project_name_short}.tags WHERE tag_id IN {tuple(chunk)};
                    """,
                )

                conn.commit()
