import psycopg2

from .. import utils

event_types = utils.get_df("event_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in event_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.event_types (
                    event_type_id,
                    device_type_id,
                    name_short,
                    name_long
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (event_type_id)
                DO UPDATE SET
                    device_type_id = EXCLUDED.device_type_id,
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long;
                """,
                (
                    row["event_type_id"],
                    row["device_type_id"],
                    row["name_short"],
                    row["name_long"],
                ),
            )
