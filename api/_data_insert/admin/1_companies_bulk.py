import logging
import uuid

import psycopg2
from app import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# List of all companies to insert
COMPANIES = [
    "SOLV Energy",
    "Mortenson",
    "Fluence",
    "Stantec",
    "Black and Veatch",
    "Burns and McDonnell",
    "Swinerton Renewable Energy",
    "Blattner Energy",
    "RES (Renewable Energy Systems)",
    "Turner Construction",
    "Kiewit Corporation",
    "Bechtel",
    "Skanska",
    "PCL Construction",
    "Clark Construction",
    "Sundt Construction",
    "Hensel Phelps",
    "Hoffman Construction",
    "IEA (Infrastructure and Energy Alternatives)",
    "Signal Energy Constructors",
    "Rosendin Electric",
    "Bombard Electric",
    "Wanzek Construction",
    "MasTec",
    "Power Engineers",
    "Wood",
    "Zachry Group",
    "NextEra",
    "Berkshire Hathaway Energy",
    "Duke Energy Renewables",
    "Avangrid Renewables",
    "Invenergy",
    "EDF Renewables",
    "Orsted",
    "Canadian Solar",
    "Pattern Energy",
    "Brookfield Renewable",
    "AES Corporation",
    "NRG Energy",
    "Vistra Energy",
    "Calpine Corporation",
    "LS Power",
    "Energy Capital Partners",
    "Terra-Gen",
    "Clearway Energy",
    "Cypress Creek Renewables",
    "Silicon Ranch",
    "Recurrent Energy",
    "Avantus",
    "ConnectGen",
    "Lightsource bp",
    "Ranger Power",
    "Pine Gate Renewables",
    "Arevon Energy",
    "Hecate Energy",
    "Primergy Solar",
    "D. E. Shaw Renewable Investments",
    "Sol Systems",
    "Pivot Energy",
    "groSolar",
    "Standard Solar",
    "Southern Current",
    "Consolidated Edison Development",
    "OCI Solar Power",
    "Sempra Infrastructure",
    "Goldman Sachs Renewable Power",
    "JPMorgan Asset Management",
    "BlackRock",
    "KKR",
    "TPG",
    "Southern Company",
    "Dominion Energy",
    "Xcel Energy",
    "Public Service Enterprise Group (PSEG)",
    "Arizona Public Service (APS)",
    "Nevada Energy",
    "Hawaiian Electric",
    "Florida Power & Light (NextEra subsidiary)",
    "Pacific Gas & Electric (PG&E)",
    "Southern California Edison",
    "Sunfolding",
    "Array Technologies",
    "GameChange Solar",
    "Nextracker",
    "RWE",
]


def create_company_name_short(company_name_long):
    """Create a short name from the long company name"""
    # Remove parentheses and their contents
    import re

    name = re.sub(r"\([^)]*\)", "", company_name_long)
    # Replace spaces and special characters with underscores, convert to lowercase
    name = re.sub(r"[^a-zA-Z0-9]", "_", name)
    # Remove multiple consecutive underscores
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores
    name = name.strip("_").lower()
    return name


def main():
    logging.info(f"Preparing to insert {len(COMPANIES)} companies into the database")

    # Display all companies that will be inserted
    for i, company in enumerate(COMPANIES, 1):
        create_company_name_short(company)

    # Proceed with bulk insertion
    logging.info("Proceeding with bulk insertion...")

    # Connect to database and perform bulk insertion
    try:
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                inserted_count = 0
                skipped_count = 0

                for company_name_long in COMPANIES:
                    company_id = uuid.uuid4()
                    company_name_short = create_company_name_short(company_name_long)

                    try:
                        # Check if company already exists
                        cur.execute(
                            "SELECT COUNT(*) FROM admin.companies WHERE name_long = %s OR name_short = %s",
                            (company_name_long, company_name_short),
                        )

                        if cur.fetchone()[0] > 0:
                            logging.warning(
                                f"Company already exists, skipping: {company_name_long}"
                            )
                            skipped_count += 1
                            continue

                        # Insert the company
                        cur.execute(
                            "INSERT INTO admin.companies (company_id, name_short, name_long) VALUES (%s, %s, %s)",
                            (str(company_id), company_name_short, company_name_long),
                        )

                        logging.info(
                            f"Inserted: {company_name_long} (ID: {company_id})"
                        )
                        inserted_count += 1

                    except psycopg2.Error as e:
                        logging.error(f"Error inserting {company_name_long}: {e}")
                        # Continue with next company instead of failing completely
                        continue

                # Commit all changes
                conn.commit()
                logging.info(
                    f"Bulk insertion completed! Inserted: {inserted_count}, Skipped: {skipped_count}"
                )

    except psycopg2.Error as e:
        logging.error(f"Database connection error: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
