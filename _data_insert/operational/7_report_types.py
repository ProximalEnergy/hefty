import psycopg2

from .. import utils

report_types = utils.get_df("report_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in report_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.report_types (
                    report_type_id,
                    name_short,
                    name_long,
                    doc_url
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (report_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long,
                    doc_url = EXCLUDED.doc_url;
                """,
                (
                    row["report_type_id"],
                    row["name_short"],
                    row["name_long"],
                    row["doc_url"],
                ),
            )
