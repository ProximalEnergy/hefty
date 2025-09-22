import psycopg2

from .. import utils

failure_modes = utils.get_df("failure_modes")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in failure_modes.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.failure_modes (
                    failure_mode_id,
                    device_type_id,
                    name_short,
                    name_long
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (failure_mode_id)
                DO UPDATE SET
                    device_type_id = EXCLUDED.device_type_id,
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long;
                """,
                (
                    row["failure_mode_id"],
                    row["device_type_id"],
                    row["name_short"],
                    row["name_long"],
                ),
            )
