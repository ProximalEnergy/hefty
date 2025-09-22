import psycopg2

from .. import utils

racking_types = utils.get_df("racking_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in racking_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.racking_types (
                    racking_type_id,
                    name_short
                )
                VALUES (%s, %s)
                On CONFLICT (racking_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short;
                """,
                (
                    row["racking_type_id"],
                    row["name_short"],
                ),
            )

        conn.commit()
