import psycopg2

from .. import utils

kpi_instances = utils.get_df("kpi_instances")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in kpi_instances.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.kpi_instances (
                    project_id,
                    kpi_type_id,
                    is_visible
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (project_id, kpi_type_id)
                DO UPDATE SET
                    is_visible = EXCLUDED.is_visible;
                """,
                (
                    row["project_id"],
                    row["kpi_type_id"],
                    row["is_visible"],
                ),
            )

    conn.commit()
