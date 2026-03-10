import psycopg2

from .. import utils

kpi_types = utils.get_df("kpi_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in kpi_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.kpi_types (
                    kpi_type_id,
                    device_type_id,
                    project_type_id,
                    name_short,
                    name_long,
                    name_metric,
                    description,
                    unit,
                    aggregation_method,
                    doc_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kpi_type_id)
                DO UPDATE SET
                    device_type_id = EXCLUDED.device_type_id,
                    project_type_id = EXCLUDED.project_type_id,
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long,
                    name_metric = EXCLUDED.name_metric,
                    description = EXCLUDED.description,
                    unit = EXCLUDED.unit,
                    aggregation_method = EXCLUDED.aggregation_method,
                    doc_url = EXCLUDED.doc_url;
                """,
                (
                    row["kpi_type_id"],
                    row["device_type_id"],
                    row["project_type_id"],
                    row["name_short"],
                    row["name_long"],
                    row["name_metric"],
                    row["description"],
                    row["unit"],
                    row["aggregation_method"],
                    row["doc_url"],
                ),
            )
