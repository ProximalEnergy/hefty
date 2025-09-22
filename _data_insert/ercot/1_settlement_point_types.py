import psycopg2

from .. import utils

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as curs:
        curs.execute(
            """
            INSERT INTO ercot.settlement_point_types
            VALUES
                (1, 'resource_node', 'Resource Node'),
                (2, 'load_zone', 'Load Zone'),
                (3, 'trading_hub', 'Trading Hub'),
                (4, 'dc_tie', 'DC Tie')
            ON CONFLICT (settlement_point_type_id) DO UPDATE
            SET name_short = EXCLUDED.name_short,
                name_long = EXCLUDED.name_long;
            """,
        )

        conn.commit()
