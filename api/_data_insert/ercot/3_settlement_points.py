import psycopg2

from .. import utils

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as curs:
        curs.execute(
            """
            INSERT INTO ercot.settlement_points (name, settlement_point_type_id, load_zone_id, trading_hub_id)
            VALUES
                ('HB_BUSAVG', 3, null, null),
                ('HB_HOUSTON', 3, null, null),
                ('HB_HUBAVG', 3, null, null),
                ('HB_NORTH', 3, null, null),
                ('HB_PAN', 3, null, null),
                ('HB_SOUTH', 3, null, null),
                ('HB_WEST', 3, null, null),
                ('LZ_AEN', 2, null, null),
                ('LZ_CPS', 2, null, null),
                ('LZ_HOUSTON', 2, null, null),
                ('LZ_LCRA', 2, null, null),
                ('LZ_NORTH', 2, null, null),
                ('LZ_RAYBN', 2, null, null),
                ('LZ_SOUTH', 2, null, null),
                ('LZ_WEST', 2, null, null),
                ('LZ_AEN_EW', 2, null, null),
                ('LZ_CPS_EW', 2, null, null),
                ('LZ_HOUSTON_EW', 2, null, null),
                ('LZ_LCRA_EW', 2, null, null),
                ('LZ_NORTH_EW', 2, null, null),
                ('LZ_RAYBN_EW', 2, null, null),
                ('LZ_SOUTH_EW', 2, null, null),
                ('LZ_WEST_EW', 2, null, null),
                ('DC_E', 4, null, null),
                ('DC_L', 4, null, null),
                ('DC_N', 4, null, null),
                ('DC_R', 4, null, null),
                ('DC_E_EW', 4, null, null),
                ('DC_L_EW', 4, null, null),
                ('DC_N_EW', 4, null, null),
                ('DC_R_EW', 4, null, null)
            ON CONFLICT (name) DO UPDATE
            SET settlement_point_type_id = EXCLUDED.settlement_point_type_id,
                load_zone_id = EXCLUDED.load_zone_id,
                trading_hub_id = EXCLUDED.trading_hub_id;
            """,
        )

        conn.commit()
