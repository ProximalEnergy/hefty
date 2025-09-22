import psycopg2

from .. import utils

expected_metric_types = utils.get_df("expected_metric_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in expected_metric_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.expected_metric_types (
                    expected_metric_type_id,
                    name_short,
                    name_long
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (expected_metric_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long;
                """,
                (
                    row["expected_metric_type_id"],
                    row["name_short"],
                    row["name_long"],
                ),
            )
