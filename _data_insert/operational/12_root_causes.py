import psycopg2

from .. import utils

root_causes = utils.get_df("root_causes")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in root_causes.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.root_causes (
                    root_cause_id,
                    device_type_id,
                    name_short,
                    name_long
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (root_cause_id)
                DO UPDATE SET
                    device_type_id = EXCLUDED.device_type_id,
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long;
                """,
                (
                    row["root_cause_id"],
                    row["device_type_id"],
                    row["name_short"],
                    row["name_long"],
                ),
            )
