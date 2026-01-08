import sys
from io import StringIO

import pandas as pd
import psycopg2

from .. import utils

project_name_short = "<project_name_short>"

# grab project name from command line
if len(sys.argv) > 1:
    project_name_short = sys.argv[1]

pv_dc_combiners = pd.read_excel(
    utils.EXCEL_PATH / f"{project_name_short}.xlsx",
    sheet_name="pv_dc_combiners",
)
pv_dc_combiners = utils.clean_df(pv_dc_combiners)

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        with StringIO() as sio:
            # NOTE: \t used because WKT data contains commas
            sio.write(pv_dc_combiners.to_csv(sep="\t", index=False, header=False))
            sio.seek(0)

            cursor.execute(
                f"""
                CREATE TEMP TABLE temp_{project_name_short}_pv_dc_combiners AS
                SELECT * FROM {project_name_short}.pv_dc_combiners
                WITH NO DATA;
                """,
            )

            cursor.copy_from(
                sio,
                f"temp_{project_name_short}_pv_dc_combiners",
                columns=pv_dc_combiners.columns,
                sep="\t",
                null="",
            )

            cursor.execute(
                f"""
                INSERT INTO {project_name_short}.pv_dc_combiners
                SELECT * FROM temp_{project_name_short}_pv_dc_combiners
                ON CONFLICT (device_id)
                DO UPDATE SET
                    modules_per_pv_source_circuit =
                        EXCLUDED.modules_per_pv_source_circuit,
                    modules_per_combiner = EXCLUDED.modules_per_combiner,
                    pv_module_id = EXCLUDED.pv_module_id;
                """,
            )

        conn.commit()
