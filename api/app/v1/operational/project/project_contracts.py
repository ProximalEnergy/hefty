import json
import logging
import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.companies import get_companies
from app._crud.operational.contracts import create_contract as crud_create_contract
from app._crud.operational.contracts import (
    delete_contract as crud_delete_contract,
)
from app._crud.operational.contracts import (
    get_project_contracts as crud_get_project_contracts,
)
from app._crud.operational.documents import get_project_documents
from app._dependencies import authentication
from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed
from core import models

from .project_documents import generate_presigned_url


def validate_and_clean_date(*, date_string: str | None) -> str | None:
    """Validate and clean date strings from AI analysis.
        Returns None for invalid dates, ensuring frontend doesn't crash.

    Args:
        date_string: Description for date_string.
    """
    if not date_string or not isinstance(date_string, str):
        return None

    try:
        # Check if it's a valid date format (YYYY-MM-DD)
        date_regex = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_regex, date_string):
            return None

        # Try to parse and validate the date
        parsed_date = datetime.strptime(date_string, "%Y-%m-%d")

        # Check reasonable year range
        if parsed_date.year < 1900 or parsed_date.year > 2100:
            return None

        return date_string
    except (ValueError, TypeError):
        return None


router = APIRouter(
    prefix="/contracts",
    tags=["project_contracts"],
)


@router.post(
    "",
    response_model=interfaces.Contract,
    operation_id="create_contract",
)
async def create_contract_route(
    project_id: UUID,
    contract: interfaces.ContractCreate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    # Create contract data
    """todo

    Args:
        project_id: Description for project_id.
        contract: Description for contract.
        db: Description for db.
        user_data: Description for user_data.
    """
    contract_data = contract.model_dump()
    contract_data["project_id"] = project_id
    contract_data["company_id_provider"] = user_data.company_id

    # Map provided category name to id if needed
    if contract_data.get("contract_category_id") is None and contract_data.get(
        "contract_category_name_short"
    ):
        name_short = contract_data["contract_category_name_short"]
        result = await db.execute(
            sa.text(
                "SELECT contract_category_id FROM operational.contract_categories "
                "WHERE name_short = :name_short"
            ),
            {"name_short": name_short},
        )
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=400, detail="Invalid contract_category_name_short"
            )
        contract_data["contract_category_id"] = row[0]

    # Remove helper field not in DB
    contract_data.pop("contract_category_name_short", None)

    return await crud_create_contract(
        db=db,
        contract=interfaces.ContractCreate(**contract_data),
    )


@router.get(
    "",
    response_model=list[interfaces.ContractWithCompany],
    operation_id="get_project_contracts",
)
async def get_project_contracts_route(
    project_id: UUID,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[UserAuthed, Depends(authentication.get_user)],
):
    # Retrieve all contracts for the project
    """todo

    Args:
        project_id: Description for project_id.
        project_db: Description for project_db.
        user: Description for user.
    """
    project_contracts = await crud_get_project_contracts(
        project_db,
        project_id=project_id,
        company_ids=[user.company_id],
    )

    # Convert SQLAlchemy Row objects to dictionaries and add document URLs
    contracts_with_urls = []
    for row in project_contracts:
        contract = row._mapping
        contract_dict = {
            "contract_id": contract["contract_id"],
            "project_id": contract["project_id"],
            "document_id": contract["document_id"],
            "company_id_provider": contract["company_id_provider"],
            "company_id_counter": contract["company_id_counter"],
            "execution_date": contract["execution_date"],
            "contract_category_id": contract.get("contract_category_id"),
            "category_name_short": contract.get("category_name_short"),
            "category_name_long": contract.get("category_name_long"),
            "term_start_date": contract.get("term_start_date"),
            "term_end_date": contract.get("term_end_date"),
            "counter_contact_addressee": contract.get("counter_contact_addressee"),
            "counter_contact_email": contract.get("counter_contact_email"),
            "counter_contact_address": contract.get("counter_contact_address"),
            "contract_summary": contract.get("contract_summary"),
            "name_short": contract["name_short"],
            "name_long": contract["name_long"],
            "s3_key": contract.get("s3_key"),
            "openai_file_id": contract.get("openai_file_id"),
        }
        if contract_dict["s3_key"]:
            contract_dict["document_url"] = generate_presigned_url(
                file_key=contract_dict["s3_key"],
            )
        else:
            contract_dict["document_url"] = None
        contracts_with_urls.append(contract_dict)

    return contracts_with_urls


@router.get("/{contract_id}/kpis")
async def get_contract_kpis_route(
    contract_id: int,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        contract_id: Description for contract_id.
        db: Description for db.
    """
    query = (
        sa.select(
            models.ContractKPI.contract_id,
            models.ContractKPI.kpi_type_id,
            models.ContractKPI.threshold,
            models.ContractKPI.liquidated_damages,
            models.ContractKPI.claim_howto,
            models.ContractKPI.provider_responsible,
            models.KPIType.name_long.label("kpi_name_long"),
            models.KPIType.name_short.label("kpi_name_short"),
            models.KPIType.unit.label("unit"),
        )
        .join(
            models.KPIType,
            models.ContractKPI.kpi_type_id == models.KPIType.kpi_type_id,
        )
        .where(models.ContractKPI.contract_id == contract_id)
    )
    result = await db.execute(query)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


def call_contract_analyzer(*, file_id: str, user_company_name: str | None = None):
    """Call OpenAI with structured function calling to extract contract fields.
        This ensures reliable JSON output without syntax errors.

    Args:
        file_id: Description for file_id.
        user_company_name: Description for user_company_name.
    """
    client = OpenAI()

    tools = [
        {
            "type": "function",
            "name": "extract_contract_fields",
            "description": "Extract contract information from a document",
            "parameters": {  # JSON Schema
                "type": "object",
                "properties": {
                    "contract_category": {
                        "type": "string",
                        "enum": [
                            "PPA",
                            "Capacity Payment/Tolling Agreement",
                            "O&M Contract",
                            "QSE Contract",
                            "Property Insurance",
                            "Land Lease",
                            "Inverter Warranty",
                            "BESS Warranty",
                            "PV Module Warranty",
                            "Warranty Claim Form",
                            "Other",
                        ],
                    },
                    "counterparty_name": {"type": "string", "nullable": True},
                    "execution_date": {
                        "type": "string",
                        "format": "date",
                        "nullable": True,
                    },
                    "term_start_date": {
                        "type": "string",
                        "format": "date",
                        "nullable": True,
                    },
                    "term_end_date": {
                        "type": "string",
                        "format": "date",
                        "nullable": True,
                    },
                    "counter_contact_addressee": {
                        "type": "string",
                        "nullable": True,
                    },
                    "counter_contact_address": {"type": "string", "nullable": True},
                    "counter_contact_email": {"type": "string", "nullable": True},
                    "contract_summary": {"type": "string", "nullable": True},
                    "important_dates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "date": {
                                    "type": "string",
                                    "format": "date",
                                    "nullable": True,
                                },
                                "description": {"type": "string", "nullable": True},
                            },
                            "required": ["title", "date", "description"],
                            "additionalProperties": False,
                        },
                    },
                    "source_references": {
                        "type": "object",
                        "properties": {
                            "contract_category": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found "
                                            "(e.g., 'in section 2.1', 'on page 3', "
                                            "'in the introduction')"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "counterparty_name": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "execution_date": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "term_start_date": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "term_end_date": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "counter_contact_addressee": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "counter_contact_address": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "counter_contact_email": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                            "contract_summary": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": (
                                            "Where in the document this was found"
                                        ),
                                        "nullable": True,
                                    },
                                    "quoted_text": {
                                        "type": "string",
                                        "description": (
                                            "The exact quoted text from the document"
                                        ),
                                        "nullable": True,
                                    },
                                },
                                "nullable": True,
                            },
                        },
                        "required": [
                            "contract_category",
                            "counterparty_name",
                            "execution_date",
                            "term_start_date",
                            "term_end_date",
                            "counter_contact_addressee",
                            "counter_contact_address",
                            "counter_contact_email",
                            "contract_summary",
                        ],
                        "additionalProperties": False,
                    },
                },
                "additionalProperties": False,
            },
        }
    ]

    system_prompt = f"""
       Extract the contract fields. If unknown, use JSON null, not the string
       "null".
       For `counterparty_name`, make it the name of the company that provides
       the services. IMPORTANT: The counterparty should NOT be the user's
       company. The user's company is: {user_company_name or "not specified"}.
       The counterparty is the OTHER party in the contract that provides
       services TO the user's company.
       For `term_end_date`, you may have to calculate it based on the
       `term_start_date` and the length of the term.
       For `contract_summary`, make it 3-5 concise sentences.
       For `important_dates`, extract only such dates that involved parties
       would want to put on their calendars. For example, the end of term, the
       first renewal date, payment deadlines, etc. Return at most 5 dates.

       For `source_references`, provide both a document location description
       and the exact quoted paragraph (max 1 sentence).
       - For location, use descriptive references like: 'in section 2.1',
       'on page 3', 'in the introduction', 'in the terms section',
       'in the contact information', etc.
       - For quoted_text, provide the exact text from the document that
       supports your extraction. Example: location: 'in section 1.5',
       quoted_text: 'This Agreement shall commence on January 1, 2024'.",
    """

    resp = client.responses.create(  # type: ignore
        model="gpt-5-mini",  # good at tool calling; use your preferred
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt,
                    },
                    {"type": "input_file", "file_id": file_id},
                ],
            }
        ],
        tools=tools,
        tool_choice={
            "type": "function",
            "name": "extract_contract_fields",
        },  # force single function
        max_output_tokens=6000,
        reasoning={"effort": "minimal"},
    )

    logging.info(f"Response: {resp}")
    logging.info(f"Response output: {resp.output}")

    # The SDK surfaces tool calls in resp.output. Grab the args:
    tool_calls = [o for o in resp.output if o.type == "function_call"]
    if not tool_calls:
        raise RuntimeError("Model didn't call the function.")

    args = tool_calls[0].arguments
    if isinstance(args, str):
        args = json.loads(args)

    logging.info(f"Parsed arguments: {args}")
    return args


@router.post("/analyze-document/{document_id}")
async def analyze_contract_document(
    document_id: UUID,
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Analyze a contract document using OpenAI File Search to extract contract
    fields. This endpoint uses the document's OpenAI file_id to perform semantic
    search and extract structured contract information using structured function
    calling.

    Args:
        document_id: Description for document_id.
        project_id: Description for project_id.
        db: Description for db.
        user: Description for user.
    """
    try:
        # Get the document to access its OpenAI file_id
        documents = await get_project_documents(
            db=db, document_ids=[document_id], project_ids=[project_id]
        )

        if not documents:
            raise HTTPException(status_code=404, detail="Document not found")

        document = documents[0]

        # Get user's company name to exclude it from counterparty identification
        user_company_name = None
        try:
            companies = await get_companies(
                db=db,
                company_ids=[user.company_id],
            )
            if companies and companies[0].name_long:
                user_company_name = companies[0].name_long
                logging.info(f"User's company: {user_company_name}")
        except Exception as e:
            logging.warning(f"Failed to get user's company name: {e}")

        # Use structured function calling to ensure reliable JSON output
        try:
            parsed_result = call_contract_analyzer(
                file_id=document.openai_file_id, user_company_name=user_company_name
            )

            # Clean and validate dates before returning to frontend
            if isinstance(parsed_result, dict):
                # Validate all date fields
                date_fields = ["execution_date", "term_start_date", "term_end_date"]
                for field in date_fields:
                    if field in parsed_result:
                        parsed_result[field] = validate_and_clean_date(
                            date_string=parsed_result[field]
                        )

                # Validate dates in important_dates array
                if "important_dates" in parsed_result and isinstance(
                    parsed_result["important_dates"], list
                ):
                    for date_item in parsed_result["important_dates"]:
                        if isinstance(date_item, dict) and "date" in date_item:
                            date_item["date"] = validate_and_clean_date(
                                date_string=date_item["date"]
                            )

            return {
                "success": True,
                "document_id": str(document_id),
                "analysis": parsed_result,
                "message": "Contract analysis completed successfully",
            }

        except Exception as response_error:
            logging.error(f"Error using structured function calling: {response_error}")
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to analyze document using OpenAI structured "
                    "function calling"
                ),
            )

    except Exception as e:
        logging.error(f"Error analyzing contract document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze contract document: {str(e)}"
        )


@router.delete("/{contract_id}")
async def delete_contract_route(
    project_id: UUID,
    contract_id: int,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Delete a contract if it has no associated Contractual KPIs.

        This endpoint will only delete contracts that don't have any Contractual
        KPIs associated with them, ensuring data integrity.

    Args:
        project_id: Description for project_id.
        contract_id: Description for contract_id.
        db: Description for db.
    """
    try:
        deleted = await crud_delete_contract(
            db=db, contract_id=contract_id, project_id=project_id
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Contract {contract_id} not found in project {project_id}",
            )

        return {
            "success": True,
            "message": f"Contract {contract_id} deleted successfully",
            "contract_id": contract_id,
        }

    except ValueError as e:
        # This is raised when contract has associated KPIs
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        logging.error(f"Error deleting contract {contract_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete contract: {str(e)}",
        )
