"""Shared helpers for OpenAI-backed AI endpoints."""

import json
import os
from typing import Any

from fastapi import HTTPException

from app.logger import logger

OpenAIClient: Any
try:
    from openai import OpenAI as _OpenAIClient
except Exception:  # pragma: no cover - optional import surface
    OpenAIClient = None
else:
    OpenAIClient = _OpenAIClient


def build_openai_responses_client() -> Any:
    """Return configured OpenAI client or raise HTTPException.

    Returns:
        OpenAI client instance.

    Raises:
        HTTPException: If SDK or API key is missing.
    """
    if OpenAIClient is None:
        logger.error("OpenAI SDK import failed (OpenAIClient is None)")
        raise HTTPException(
            status_code=500,
            detail="OpenAI SDK not available on server.",
        )

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not set in environment")
        raise HTTPException(
            status_code=500,
            detail=(
                "OpenAI API key not configured. Please set OPENAI_API_KEY "
                "environment variable."
            ),
        )

    return OpenAIClient(api_key=openai_api_key)


def extract_response_tool_json(
    *,
    response: Any,
    tool_name: str,
) -> dict[str, Any] | None:
    """Parse function_call arguments from a responses.create result.

    Args:
        response: OpenAI response object.
        tool_name: Expected function name.

    Returns:
        Parsed JSON dict or None.
    """
    try:
        outputs = getattr(response, "output", []) or []
        for item in outputs:
            if hasattr(item, "type") and item.type == "function_call":
                if getattr(item, "name", None) != tool_name:
                    continue
                parsed = _parse_tool_arguments(
                    arguments=getattr(item, "arguments", None),
                )
                if parsed is not None:
                    return parsed

            if isinstance(item, dict) and item.get("type") == "function_call":
                function_payload = item.get("function")
                function_name = (
                    function_payload.get("name")
                    if isinstance(function_payload, dict)
                    else None
                )
                name = item.get("name") or function_name
                if name != tool_name:
                    continue
                arguments = item.get("arguments")
                if not arguments and isinstance(function_payload, dict):
                    arguments = function_payload.get("arguments")
                parsed = _parse_tool_arguments(arguments=arguments)
                if parsed is not None:
                    return parsed
    except Exception:
        return None

    return None


def _parse_tool_arguments(*, arguments: Any) -> dict[str, Any] | None:
    """Return tool-call arguments as a dict when available."""
    if not arguments:
        return None
    parsed = arguments if isinstance(arguments, dict) else json.loads(arguments)
    return parsed if isinstance(parsed, dict) else None
