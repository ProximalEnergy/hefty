import logging
import uuid

import psycopg2
from openai import OpenAI

from .. import utils

COMPANY_NAME_SHORT = "<company_name_short>"
PROJECT_NAME_SHORT = "<project_name_short>"

logging.basicConfig(level=logging.INFO)


def get_company_id_from_name_short(*, name_short: str) -> uuid.UUID:
    """Look up a company ID by its short name.

    Args:
        name_short: Short name for the company.
    """
    with psycopg2.connect(utils.CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT company_id FROM admin.companies WHERE name_short = %s",
                (name_short,),
            )
            result = cur.fetchone()
            if result is None:
                raise ValueError(f"No company found with name_short: {name_short}")
            return result[0]


def get_project_id_from_name_short(*, name_short: str) -> uuid.UUID:
    """Look up a project ID by its short name.

    Args:
        name_short: Short name for the project.
    """
    with psycopg2.connect(utils.CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT project_id FROM operational.projects WHERE name_short = %s",
                (name_short,),
            )
            result = cur.fetchone()
            if result is None:
                raise ValueError(f"No project found with name_short: {name_short}")
            return result[0]


def create_vector_store(*, name: str) -> str:
    """Create an OpenAI vector store and return its ID.

    Args:
        name: Name to assign to the vector store.
    """
    client = OpenAI()
    vector_store = client.vector_stores.create(name=name)
    return vector_store.id


def insert_company_project_record(
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    vector_store_id: str,
) -> None:
    """Create a company-project association if it does not exist.

    Args:
        company_id: Company identifier to link.
        project_id: Project identifier to link.
        vector_store_id: Vector store identifier to associate.
    """
    with psycopg2.connect(utils.CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM admin.company_projects WHERE company_id = %s "
                "AND project_id = %s",
                (company_id, project_id),
            )
            if cur.fetchone():
                logging.warning(
                    f"Company project {company_id} {project_id} already exists",
                )
            else:
                cur.execute(
                    "INSERT INTO admin.company_projects (company_id, project_id, "
                    "vector_store_id) VALUES (%s, %s, %s)",
                    (company_id, project_id, vector_store_id),
                )
                logging.info(
                    "Created company project "
                    f"{company_id}|{project_id}|{vector_store_id}",
                )


logging.info(f"Company: {COMPANY_NAME_SHORT}")
logging.info(f"Project: {PROJECT_NAME_SHORT}")
if input("Continue? (y/n): ") != "y":
    logging.info("Exiting")
    exit()


company_id = get_company_id_from_name_short(name_short=COMPANY_NAME_SHORT)
logging.info(f"Company ID: {company_id}")
project_id = get_project_id_from_name_short(name_short=PROJECT_NAME_SHORT)
logging.info(f"Project ID: {project_id}")
vector_store_id = create_vector_store(name=f"{COMPANY_NAME_SHORT}-{PROJECT_NAME_SHORT}")
logging.info(f"Vector Store ID: {vector_store_id}")
insert_company_project_record(
    company_id=company_id,
    project_id=project_id,
    vector_store_id=vector_store_id,
)
