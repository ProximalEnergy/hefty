import psycopg2

from .. import utils

rackings = utils.get_df("rackings")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in rackings.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.rackings (
                racking_id,
                racking_type_id,
                manufacturer,
                model,
                max_rotation_angle,
                min_rotation_angle,
                wind_stow_angle,
                wind_stow_threshold,
                hail_stow_angle,
                snow_stow_angle
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (racking_id)
                DO UPDATE SET
                    racking_type_id = EXCLUDED.racking_type_id,
                    manufacturer = EXCLUDED.manufacturer,
                    model = EXCLUDED.model,
                    max_rotation_angle = EXCLUDED.max_rotation_angle,
                    min_rotation_angle = EXCLUDED.min_rotation_angle,
                    wind_stow_angle = EXCLUDED.wind_stow_angle,
                    wind_stow_threshold = EXCLUDED.wind_stow_threshold,
                    hail_stow_angle = EXCLUDED.hail_stow_angle,
                    snow_stow_angle = EXCLUDED.snow_stow_angle;
                """,
                (
                    row["racking_id"],
                    row["racking_type_id"],
                    row["manufacturer"],
                    row["model"],
                    row["max_rotation_angle"],
                    row["min_rotation_angle"],
                    row["wind_stow_angle"],
                    row["wind_stow_threshold"],
                    row["hail_stow_angle"],
                    row["snow_stow_angle"],
                ),
            )

        conn.commit()
