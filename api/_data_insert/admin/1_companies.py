import logging
import uuid

import psycopg2
from app import settings

COMPANY_NAME_LONG = "<company_name_long>"

# Check to make sure the company name is set (changed from placeholder)
if COMPANY_NAME_LONG == "<company_name_long>":
    raise ValueError("COMPANY_NAME_LONG is not set")

company_id = uuid.uuid4()  # Generate a new UUID for the company
company_name_short = COMPANY_NAME_LONG.replace(" ", "_").lower()  # Create a name_short

logging.info(
    f"Company ID: {company_id}"
    f"Company Name Short: {company_name_short}"
    f"Company Name Long: {COMPANY_NAME_LONG}",
)

# Ask the user to confirm the company details
if input("Continue? (y/n): ") != "y":
    logging.info("Exiting")
    exit()

# Connect to the database and insert the company details
with psycopg2.connect(settings.DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admin.companies (company_id, name_short, name_long) VALUES (%s, %s, %s)",
            (str(company_id), company_name_short, COMPANY_NAME_LONG),
        )

logging.info("New company added to the database!")
