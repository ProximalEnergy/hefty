import psycopg2

from .. import utils

data_types = utils.get_df("data_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in data_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.data_types (
                    data_type_id,
                    name_short
                )
                VALUES (%s, %s)
                ON CONFLICT (data_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short;
                """,
                (
                    row["data_type_id"],
                    row["name_short"],
                ),
            )

        conn.commit()
