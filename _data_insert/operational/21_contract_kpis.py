import pandas as pd
import psycopg2

from .. import utils

contract_kpis = utils.get_df("contract_kpis")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        for _, row in contract_kpis.iterrows():
            # Pass JSON fields directly as strings
            threshold = str(row["threshold"]) if pd.notna(row["threshold"]) else None
            liquidated_damages = (
                str(row["liquidated_damages"])
                if pd.notna(row["liquidated_damages"])
                else None
            )
            claim_howto = (
                str(row["claim_howto"]) if pd.notna(row["claim_howto"]) else None
            )

            cursor.execute(
                """
                INSERT INTO operational.contract_kpis (
                    contract_id,
                    kpi_type_id,
                    threshold,
                    liquidated_damages,
                    claim_howto,
                    provider_responsible
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (contract_id, kpi_type_id)
                DO UPDATE SET
                    threshold = EXCLUDED.threshold,
                    liquidated_damages = EXCLUDED.liquidated_damages,
                    claim_howto = EXCLUDED.claim_howto,
                    provider_responsible = EXCLUDED.provider_responsible;
                """,
                (
                    row["contract_id"],
                    row["kpi_type_id"],
                    threshold,
                    liquidated_damages,
                    claim_howto,
                    row["provider_responsible"],
                ),
            )
