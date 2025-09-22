import psycopg2

from .. import utils

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as curs:
        curs.execute(
            """
            INSERT INTO ercot.settlement_point_markets
            VALUES
                (1, 'day_ahead', 'Day-Ahead'),
                (2, 'real_time', 'Real-Time')
            ON CONFLICT (settlement_point_market_id) DO UPDATE
            SET name_short = EXCLUDED.name_short,
                name_long = EXCLUDED.name_long;
            """,
        )

        conn.commit()
