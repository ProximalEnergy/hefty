import pandas as pd
import psycopg2

from .. import utils

status_binary = utils.get_df("status_binary")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in status_binary.iterrows():
            cursor.execute(
                """
                INSERT INTO operational.status_binary (
                    status_binary_id,
                    bit_position,
                    description,
                    state_false,
                    state_true,
                    nominal_state,
                    failure_mode_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (status_binary_id, bit_position)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    state_false = EXCLUDED.state_false,
                    state_true = EXCLUDED.state_true,
                    nominal_state = EXCLUDED.nominal_state,
                    failure_mode_id = EXCLUDED.failure_mode_id;
                """,
                (
                    row["status_binary_id"],
                    row["bit_position"],
                    row["description"],
                    row["state_false"],
                    row["state_true"],
                    bool(row["nominal_state"])
                    if not pd.isna(row["nominal_state"])
                    else None,
                    row["failure_mode_id"],
                ),
            )

        conn.commit()
