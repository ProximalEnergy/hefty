import logging
import sys
from io import StringIO

import pandas as pd
import psycopg2

from .. import utils

if len(sys.argv) != 2:
    raise ValueError("Project name is required")

project_name_short = sys.argv[1]

tags = pd.read_excel(
    utils.EXCEL_PATH / f"{project_name_short}.xlsx",
    sheet_name="tags",
    dtype={"name_short": str, "name_long": str},
)

# Add missing columns if they do not exist
# NOTE: This is to handle projects where these columns were not created yet in Google Sheets
if "in_tsdb" not in tags.columns:
    tags["in_tsdb"] = True

if "pg_data_type_id" not in tags.columns:
    tags["pg_data_type_id"] = 0

if "status_lookup_id" not in tags.columns:
    tags["status_lookup_id"] = None

if "_to_delete" not in tags.columns:
    tags["_to_delete"] = False

# Get a list of tag_ids that are to be deleted
tag_ids_to_delete = tags[tags["_to_delete"]]["tag_id"].astype(int).tolist()

# Include only tags that are not to be deleted
tags = tags[~tags["_to_delete"]]

# Clean the DataFrame
tags = utils.clean_df(tags, index_col="tag_id")

columns = [
    "tag_id",
    "in_tsdb",
    "device_id",
    "pg_data_type_id",
    "name_scada",
]
logging.info(f"The following columns will be inserted/updated: {columns}")

restricted_columns = [
    "sensor_type_id",
    "unit_scada",
    "unit_offset",
    "unit_scale",
]

if any(column in columns for column in restricted_columns):
    raise ValueError(
        f"The following columns should only be updated via the Tag Explorer UI: {restricted_columns}"
    )

tags = tags[columns]


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

                # Create columns string for temp table and INSERT statement
                columns_str = ", ".join(columns)

                cursor.execute(
                    f"""
                    CREATE TEMP TABLE temp_{project_name_short}_tags AS
                    SELECT {columns_str} FROM {project_name_short}.tags
                    WITH NO DATA;
                    """,
                )

                cursor.copy_from(
                    sio,
                    f"temp_{project_name_short}_tags",
                    columns=columns,
                    sep="\t",
                    null="",
                )

                cursor.execute(
                    f"""
                    INSERT INTO {project_name_short}.tags ({columns_str})
                    SELECT {columns_str} FROM temp_{project_name_short}_tags
                    ON CONFLICT (tag_id)
                    DO UPDATE SET
                        device_id = EXCLUDED.device_id,
                        in_tsdb = EXCLUDED.in_tsdb,
                        pg_data_type_id = EXCLUDED.pg_data_type_id,
                        name_scada = EXCLUDED.name_scada;
                    """,
                )

                conn.commit()


CHUNK_SIZE = 50000  # Number of tags to process per chunk
# Process tags in chunks of CHUNK_SIZE
for start in range(0, len(tags), CHUNK_SIZE):
    end = start + CHUNK_SIZE
    tag_chunk = tags.iloc[start:end]
    logging.info(
        f"Processing tag chunk {start // CHUNK_SIZE + 1} of {(len(tags) - 1) // CHUNK_SIZE + 1}"
    )
    process_tag_chunk(tag_chunk)

# # Delete tags that are to be deleted, chunked by 1000
# with psycopg2.connect(
#     utils.CONNECTION_STRING,
#     application_name=utils.application_name(__file__),
# ) as conn:
#     with conn.cursor() as cursor:
#         for i in range(0, len(tag_ids_to_delete), 1000):
#             logging.info(
#                 f"Deleting chunk {(i // 1000) + 1} of {(len(tag_ids_to_delete) // 1000) + 1}",
#             )
#             chunk = tag_ids_to_delete[i : i + 1000]

#             cursor.execute(
#                 f"""
#                 DELETE FROM {project_name_short}.tags WHERE tag_id IN {tuple(chunk)};
#                 """,
#             )

#             conn.commit()

logging.info("✅ Completed!")
