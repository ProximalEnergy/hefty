import psycopg2

from .. import utils

status_lookup = utils.get_df("status_lookup")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in status_lookup.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.status_lookup (
                    status_lookup_id,
                    name_short,
                    name_long,
                    status_binary_id,
                    status_string_id,
                    status_boolean_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (status_lookup_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long,
                    status_binary_id = EXCLUDED.status_binary_id,
                    status_string_id = EXCLUDED.status_string_id,
                    status_boolean_id = EXCLUDED.status_boolean_id;
                """,
                (
                    row["status_lookup_id"],
                    row["name_short"],
                    row["name_long"],
                    row["status_binary_id"],
                    row["status_string_id"],
                    row["status_boolean_id"],
                ),
            )

        conn.commit()
