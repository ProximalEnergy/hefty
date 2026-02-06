import psycopg2

from .. import utils

device_types = utils.get_df("device_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in device_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.device_types
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (device_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long,
                    description = EXCLUDED.description;
                """,
                (
                    row["device_type_id"],
                    row["name_short"],
                    row["name_long"],
                    row["description"],
                ),
            )

        conn.commit()
