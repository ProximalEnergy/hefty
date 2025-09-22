import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from app.dependencies import get_user_data_async
from app.interfaces import UserData

router = APIRouter(prefix="/ai", tags=["ai"])


class VoiceChatSessionRequest(BaseModel):
    model: str = "gpt-realtime"


class VoiceChatSessionResponse(BaseModel):
    client_secret: str
    expires_at: str


@router.post("/voice-chat/session", response_model=VoiceChatSessionResponse)
async def create_voice_chat_session(
    request: VoiceChatSessionRequest, user_data: UserData = Depends(get_user_data_async)
):
    """
    Create a new voice chat session by generating a client ephemeral token.
    This token allows the frontend to securely connect to OpenAI's Realtime GPT API.
    """
    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
            )

        # Request client secret from OpenAI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"session": {"type": "realtime", "model": request.model}},
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenAI API error: {response.text}",
                )

            data = response.json()

            # Check the actual response structure and handle it accordingly
            if "value" in data:
                # Direct structure (what OpenAI actually returns)
                client_secret = data["value"]
                expires_at = data.get("expires_at", "unknown")

                # Convert timestamp to string if it's an integer
                if isinstance(expires_at, int):
                    from datetime import datetime

                    expires_at = datetime.fromtimestamp(expires_at).isoformat()

            elif "client_secret" in data:
                # Expected structure (fallback)
                client_secret = data["client_secret"]["value"]
                expires_at = data["client_secret"]["expires_at"]
            elif "secret" in data:
                # Alternative structure (fallback)
                client_secret = data["secret"]["value"]
                expires_at = data["secret"]["expires_at"]
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected OpenAI API response structure. Please check the backend logs for details.",
                )

            return VoiceChatSessionResponse(
                client_secret=client_secret,
                expires_at=expires_at,
            )

    except httpx.TimeoutException as e:
        raise HTTPException(status_code=408, detail="Request to OpenAI API timed out")
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to communicate with OpenAI API: {str(e)}"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class EnsureVectorStoreRequest(BaseModel):
    openai_file_id: str
    name: str | None = None


class EnsureVectorStoreResponse(BaseModel):
    vector_store_id: str


@router.post("/vector-store/ensure", response_model=EnsureVectorStoreResponse)
async def ensure_vector_store(
    request: EnsureVectorStoreRequest,
    user_data: UserData = Depends(get_user_data_async),
):
    """
    Ensure an OpenAI vector store exists for the provided file id. If needed, create it.
    Returns the vector_store_id.
    """
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
            )

        client = OpenAI(api_key=openai_api_key)

        # First, check if a vector store already exists for this file
        existing_stores = client.vector_stores.list()
        for store in existing_stores.data:
            # Check if this store contains our file
            store_files = client.vector_stores.files.list(vector_store_id=store.id)
            for file in store_files.data:
                if file.id == request.openai_file_id and store.status == "completed":
                    # Found an existing completed vector store with this file
                    return EnsureVectorStoreResponse(vector_store_id=store.id)

        # If no existing store found, create a new one
        vs = client.vector_stores.create(
            name=request.name or "aria-knowledge",
            file_ids=[request.openai_file_id],
        )
        return EnsureVectorStoreResponse(vector_store_id=vs.id)
    except Exception as e:  # pragma: no cover - surface error details
        raise HTTPException(
            status_code=500, detail=f"Failed to ensure vector store: {str(e)}"
        )
