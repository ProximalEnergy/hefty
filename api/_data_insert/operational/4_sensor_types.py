import psycopg2

from .. import utils

sensor_types = utils.get_df("sensor_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in sensor_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.sensor_types
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sensor_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long,
                    name_metric = EXCLUDED.name_metric,
                    unit = EXCLUDED.unit,
                    device_type_id = EXCLUDED.device_type_id,
                    description = EXCLUDED.description;
                """,
                (
                    row["sensor_type_id"],
                    row["name_short"],
                    row["name_long"],
                    row["name_metric"],
                    row["unit"],
                    row["device_type_id"],
                    row["description"],
                ),
            )

        conn.commit()
