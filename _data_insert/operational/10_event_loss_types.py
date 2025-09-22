import psycopg2

from .. import utils

event_loss_types = utils.get_df("event_loss_types")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in event_loss_types.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.event_loss_types (
                    event_loss_type_id,
                    name_short
                )
                VALUES (%s, %s)
                ON CONFLICT (event_loss_type_id)
                DO UPDATE SET
                    name_short = EXCLUDED.name_short;
                """,
                (
                    row["event_loss_type_id"],
                    row["name_short"],
                ),
            )
