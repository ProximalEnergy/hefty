import psycopg2

from .. import utils

company_permissions = utils.get_df("company_permissions")

with psycopg2.connect(
    utils.CONNECTION_STRING,
    application_name=utils.application_name(__file__),
) as conn:
    with conn.cursor() as cursor:
        # Drop existing data to avoid duplicates
        cursor.execute("DELETE FROM admin.company_permissions")

        # Prepare the data for bulk insert
        insert_values = [
            (row["company_id"], row["permission_id"], row["project_id"])
            for _, row in company_permissions.iterrows()
        ]

        # Execute the bulk insert
        cursor.executemany(
            """
            INSERT INTO admin.company_permissions (
                company_id,
                permission_id,
                project_id
            )
            VALUES (%s, %s, %s);
            """,
            insert_values,
        )

        conn.commit()
