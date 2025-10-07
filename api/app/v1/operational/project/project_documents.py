import asyncio
import logging
from typing import Annotated
from uuid import UUID

import boto3
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.companies import get_companies
from app._crud.admin.company_projects import (
    create_company_project,
    get_company_projects,
)
from app._crud.operational.contracts import (
    get_contracts_by_document_id as crud_get_contracts_by_document_id,
)
from app._crud.operational.contracts import (
    get_project_contracts as crud_get_project_contracts,
)
from app._crud.operational.documents import (
    create_project_document as crud_create_project_document,
)
from app._crud.operational.documents import (
    delete_project_document as crud_delete_project_document,
)
from app._crud.operational.documents import (
    get_project_documents as crud_get_project_documents,
)
from core import models

BUCKET_NAME = "proximal-am-documents"
REGION_NAME = "us-east-2"


router = APIRouter(
    prefix="/projects/{project_id}/documents",
    tags=["project_documents"],
)


def generate_presigned_url(*, file_key: str) -> str:
    # Generate a pre-signed URL for a file
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": file_key,
        },
        ExpiresIn=3600,  # Link expiration in seconds (1 hour)
    )
    return presigned_url


@router.get("/", response_model=list[interfaces.Document])
async def get_project_documents(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[interfaces.UserData, Depends(dependencies.get_user_data_async)],
):
    project_documents = await crud_get_project_documents(
        db=db,
        project_ids=[project_id],
        company_ids=[user.company_id],
    )

    project_contracts = await crud_get_project_contracts(db=db, project_id=project_id)
    contract_map = {
        c[2]: c[14] for c in project_contracts
    }  # c[2] = document_id, c[14] = company name_long

    response_documents = []
    for d in project_documents:
        response_documents.append(
            interfaces.Document(
                document_id=d.document_id,
                name=d.s3_key.split("/")[-1],
                url=generate_presigned_url(file_key=d.s3_key),
                contract_name=contract_map.get(d.document_id),
            )
        )

    # Sort documents by name
    response_documents.sort(key=lambda x: x.name)

    return response_documents


@router.post("/", response_model=interfaces.Document)
async def upload_project_document(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[interfaces.UserData, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    file: Annotated[UploadFile, File()] = ...,  # type: ignore
):
    # Get company from user.company_id
    try:
        companies = await get_companies(
            db=db,
            company_ids=[user.company_id],
        )
        company = companies[0]
        # Access the attribute immediately within the async context
        company_name_short = company.name_short
    except IndexError:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get or create company project from user.company_id and project.project_id
    try:
        company_projects = await get_company_projects(
            db=db,
            company_ids=[user.company_id],
            project_ids=[project.project_id],
        )
        company_project = company_projects[0]

    except IndexError:
        # Company project doesn't exist, create it
        try:
            company_project = await create_company_project(
                db=db,
                company_id=user.company_id,
                project_id=project.project_id,
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Failed to create company project. Please try again or contact support.",
            )

    # Process filename to ensure extension is lowercase
    if file.filename:
        filename_parts = file.filename.rsplit(".", 1)
        if len(filename_parts) > 1:
            processed_filename = f"{filename_parts[0]}.{filename_parts[1].lower()}"
        else:
            processed_filename = file.filename  # No extension found
    else:
        # Handle case where filename might be None
        raise HTTPException(status_code=400, detail="Uploaded file must have a name")

    # Access project attributes within async context to avoid lazy loading issues
    project_name_short = project.name_short

    # Check and see if a file with the same name already exists in S3
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    file_key = (
        f"documents/{company_name_short}-{project_name_short}/{processed_filename}"
    )
    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=file_key)
        raise HTTPException(status_code=400, detail="File already exists")
    except s3_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise HTTPException(status_code=500, detail="Error checking file existence")

    # Create OpenAI client
    client = OpenAI()

    # Read the file content
    file_content = await file.read()

    try:
        # Upload to OpenAI
        file_object = client.files.create(
            file=(
                processed_filename,
                file_content,
            ),  # Include the file name with lowercase extension and content
            purpose="assistants",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to upload file to vector store. If this issue persists, "
                "please submit a feedback ticket."
            ),
        )

    try:
        # Attach file to vector store
        client.vector_stores.files.create(
            vector_store_id=company_project.vector_store_id,
            file_id=file_object.id,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to attach file to vector store. If this issue persists, "
                "please submit a feedback ticket."
            ),
        )

    try:
        # Upload the file to S3 with the correct content type
        s3_client = boto3.client("s3", region_name=REGION_NAME)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_key,
            Body=file_content,
            ContentType="application/pdf",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to upload file. If this issue persists, "
                "please submit a feedback ticket.",
            ),
        )

    document = await crud_create_project_document(
        db=db,
        company_id=user.company_id,
        project_id=project.project_id,
        s3_key=file_key,
        openai_file_id=file_object.id,
    )

    # Generate a presigned URL for the uploaded file
    presigned_url = generate_presigned_url(file_key=file_key)

    response_document = interfaces.Document(
        document_id=document.document_id,
        name=processed_filename,
        url=presigned_url,
        contract_name=None,
    )

    return response_document


@router.post("/search-contract/{document_id}")
async def search_contract_content(
    document_id: UUID,
    project_id: UUID,
    query: str,
    vector_store_id: str,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[interfaces.UserData, Depends(dependencies.get_user_data_async)],
):
    """
    Search for relevant contract content using OpenAI's Responses API with file search.
    Uses vector stores for efficient retrieval of relevant contract information.
    Returns the most relevant chunks of text based on the query.
    """
    logging.info(
        f"Starting contract search for document_id: {document_id}, query: '{query}', vector_store_id: {vector_store_id}"
    )
    try:
        # Verify the document exists and user has access
        documents = await crud_get_project_documents(
            db=db, document_ids=[document_id], project_ids=[project_id]
        )

        if not documents:
            raise HTTPException(status_code=404, detail="Document not found")

        documents[0]

        # Initialize OpenAI client
        client = OpenAI()

        # Search for relevant content directly from vector store (fastest path)
        try:
            # First, let's check the vector store status with timeout to prevent hanging
            try:
                # Poll vector store status until it's completed (with timeout)
                vector_store = client.vector_stores.retrieve(vector_store_id)
                max_polls = 10  # Maximum 20 seconds of polling
                poll_count = 0

                # Wait for vector store to be completed
                while vector_store.status == "in_progress" and poll_count < max_polls:
                    await asyncio.sleep(2)  # Wait 2 seconds between checks
                    vector_store = client.vector_stores.retrieve(vector_store_id)
                    poll_count += 1

                if vector_store.status != "completed":
                    # If vector store is not ready after timeout, try search anyway
                    # as it might still work for some files
                    pass

                # List files in the vector store and check their readiness (with timeout)
                files = client.vector_stores.files.list(vector_store_id=vector_store_id)

                for file in files.data:
                    # Poll individual files to ensure they're ready (with timeout)
                    file_poll_count = 0
                    max_file_polls = 5  # Maximum 5 seconds per file

                    if file.status == "in_progress":
                        while (
                            file.status == "in_progress"
                            and file_poll_count < max_file_polls
                        ):
                            await asyncio.sleep(1)  # Wait 1 second between checks
                            file = client.vector_stores.files.retrieve(
                                vector_store_id=vector_store_id, file_id=file.id
                            )
                            file_poll_count += 1

                    if file.status != "completed":
                        pass

                # Even if not all files are ready, try the search as it might still work
                # This prevents hanging on follow-up questions

            except Exception as vs_error:
                # Log the error but continue with search attempt
                logging.warning(
                    f"Vector store status check failed for vector_store_id {vector_store_id}: {vs_error}"
                )

            # Now try the actual query
            try:
                results = client.vector_stores.search(
                    vector_store_id=vector_store_id,
                    query=query,
                    max_num_results=3,
                )
                top = results.data

                search_results = [
                    {
                        "text": r.content[0].text,
                        "filename": r.filename,
                        "score": r.score,
                    }
                    for r in top
                ]

                logging.info(
                    f"Successfully searched contract content for query: {query}, found {len(search_results)} results"
                )
                return {"search_results": search_results}

            except Exception as search_error:
                logging.error(
                    f"Failed to search vector store {vector_store_id} with query '{query}': {search_error}"
                )
                # Return empty results instead of raising an exception to prevent hanging
                return {"search_results": []}

        except Exception as response_error:
            logging.error(
                f"Unexpected error in search_contract_content: {response_error}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to search contract content",
            )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while searching contract content",
        )


@router.delete("/{document_id}")
async def delete_project_document(
    document_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    # Check if document is associated with a contract
    associated_contracts = await crud_get_contracts_by_document_id(
        db=db, document_id=document_id
    )
    if associated_contracts:
        raise HTTPException(
            status_code=400,
            detail=(
                "This document cannot be deleted because it is associated with a "
                "contract."
            ),
        )

    # Query document
    documents = await crud_get_project_documents(db=db, document_ids=[document_id])
    document = documents[0]

    try:
        # Delete document from OpenAI
        client = OpenAI()
        client.files.delete(file_id=document.openai_file_id)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to delete file from vector store. "
                "If this issue persists, please submit a feedback ticket.",
            ),
        )

    try:
        # Delete file from S3
        s3_client = boto3.client("s3", region_name=REGION_NAME)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=document.s3_key)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to delete file. If this issue persists, "
                "please submit a feedback ticket.",
            ),
        )

    # Delete document from database
    await crud_delete_project_document(db=db, document_id=document_id)

    return JSONResponse(
        content={"message": "Document deleted successfully"},
        status_code=200,
    )
