import psycopg2

from .. import utils

status_string = utils.get_df("status_string")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in status_string.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.status_string (
                    status_string_id,
                    description,
                    string_trigger,
                    failure_mode_id
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (status_string_id, string_trigger)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    failure_mode_id = EXCLUDED.failure_mode_id;
                """,
                (
                    row["status_string_id"],
                    row["description"],
                    row["string_trigger"],
                    row["failure_mode_id"],
                ),
            )

        conn.commit()
