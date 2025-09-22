import psycopg2

from .. import utils

pg_data_types = utils.get_df("pg_data_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in pg_data_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.pg_data_types (
                    pg_data_type_id,
                    name_short
                )
                VALUES (%s, %s)
                ON CONFLICT (pg_data_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short;
                """,
                (
                    row["pg_data_type_id"],
                    row["name_short"],
                ),
            )
        conn.commit()
