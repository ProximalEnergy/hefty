import psycopg2

from .. import utils

project_types = utils.get_df("project_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in project_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.project_types
                VALUES (%s, %s, %s)
                ON CONFLICT (project_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short,
                    name_long = EXCLUDED.name_long;
                """,
                (
                    row["project_type_id"],
                    row["name_short"],
                    row["name_long"],
                ),
            )

        conn.commit()
