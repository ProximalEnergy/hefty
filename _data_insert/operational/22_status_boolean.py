import psycopg2

from .. import utils

status_boolean = utils.get_df("status_boolean")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in status_boolean.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.status_boolean (
                    status_boolean_id,
                    description,
                    state_false,
                    state_true,
                    failure_mode_id
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (status_boolean_id)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    state_false = EXCLUDED.state_false,
                    state_true = EXCLUDED.state_true,
                    failure_mode_id = EXCLUDED.failure_mode_id;
                """,
                (
                    row["status_boolean_id"],
                    row["description"],
                    row["state_false"],
                    row["state_true"],
                    row["failure_mode_id"],
                ),
            )

        conn.commit()
