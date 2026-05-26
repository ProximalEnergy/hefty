from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.v1.operational.project.project_documents import delete_project_document_route
from fastapi import HTTPException

MODULE = "app.v1.operational.project.project_documents"


@pytest.mark.asyncio
async def test_delete_project_document_route_requires_document_scope():
    """Reject deletion before side effects when document is outside caller scope."""
    project_id = uuid4()
    document_id = uuid4()
    user = MagicMock()
    user.company_id = uuid4()
    db = AsyncMock()

    with (
        patch(
            f"{MODULE}.crud_get_project_documents",
            new=AsyncMock(return_value=[]),
        ) as mock_get_documents,
        patch(
            f"{MODULE}.crud_get_contracts_by_document_id",
            new=AsyncMock(),
        ) as mock_get_contracts,
        patch(
            f"{MODULE}.crud_delete_project_document",
            new=AsyncMock(),
        ) as mock_delete_document,
        patch(f"{MODULE}.OpenAI") as mock_openai,
        patch(f"{MODULE}.boto3.client") as mock_boto,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await delete_project_document_route(
                project_id=project_id,
                document_id=document_id,
                db=db,
                user=user,
            )

    assert exc_info.value.status_code == 404
    mock_get_documents.assert_awaited_once_with(
        db=db,
        document_ids=[document_id],
        project_ids=[project_id],
        company_ids=[user.company_id],
    )
    mock_get_contracts.assert_not_awaited()
    mock_delete_document.assert_not_awaited()
    mock_openai.assert_not_called()
    mock_boto.assert_not_called()
