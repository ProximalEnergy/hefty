import psycopg2

from .. import utils

expected_metrics = utils.get_df("expected_metrics")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in expected_metrics.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.expected_metrics (
                    expected_metric_id,
                    expected_metric_type_id,
                    includes_soiling,
                    includes_warranted_degradation
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (expected_metric_id)
                DO UPDATE SET
                    expected_metric_type_id = EXCLUDED.expected_metric_type_id,
                    includes_soiling = EXCLUDED.includes_soiling,
                    includes_warranted_degradation = EXCLUDED.includes_warranted_degradation;
                """,
                (
                    row["expected_metric_id"],
                    row["expected_metric_type_id"],
                    row["includes_soiling"],
                    row["includes_warranted_degradation"],
                ),
            )
