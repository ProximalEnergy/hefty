import json
import os
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.logger import logger

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional import surface
    OpenAI = None  # type: ignore


router = APIRouter(prefix="/ai", tags=["ai"])


class SignalPair(BaseModel):
    """todo"""

    ir_signal: str | None = Field(default=None)
    rgb_signal: str | None = Field(default=None)


class RootCauseCandidate(BaseModel):
    """todo"""

    root_cause_id: int
    name_short: str | None = None
    name_long: str | None = None
    device_type_id: int


class SuggestRootCauseRequest(BaseModel):
    """todo"""

    pairs: list[SignalPair]
    candidates: list[RootCauseCandidate]
    model: str = Field(default="gpt-5-mini")


class SuggestedRootCause(BaseModel):
    """todo"""

    index: int
    root_cause_id: int | None
    confidence: float | None = None
    rationale: str | None = None


class SuggestRootCauseResponse(BaseModel):
    """todo"""

    suggestions: list[SuggestedRootCause]


@router.post(
    "/root-cause/suggest",
    response_model=SuggestRootCauseResponse,
)
async def suggest_root_cause(
    *,
    request: SuggestRootCauseRequest,
):
    """Suggest a root cause for each (IR, RGB) signal pair.

        Uses OpenAI Responses API to select the best candidate root cause
        id from the provided list, based on IR/RGB signals.

    Args:
        request: Description for request.
    """
    if OpenAI is None:
        logger.error("OpenAI SDK import failed (OpenAI is None)")
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

    client = OpenAI(api_key=openai_api_key)

    if not request.pairs:
        raise HTTPException(status_code=400, detail="pairs must be non-empty")
    if not request.candidates:
        raise HTTPException(status_code=400, detail="candidates must be non-empty")

    # Build prompt and schema for structured selection
    pairs_payload = [
        {
            "index": idx,
            "ir_signal": (p.ir_signal or "").strip(),
            "rgb_signal": (p.rgb_signal or "").strip(),
        }
        for idx, p in enumerate(request.pairs)
    ]
    candidates_payload = [c.model_dump() for c in request.candidates]

    system_prompt = (
        "You are an expert at classifying solar asset anomalies. "
        "Given IR and RGB signal descriptors and a list of allowed "
        "root cause candidates, select the best matching root_cause_id "
        "for each pair. If uncertain, return null and explain briefly. "
        "String Outage events that are not related to a broken module, should "
        "be classified as `DC Field Connector Broken`"
    )

    user_prompt = {
        "task": "select_root_cause",
        "pairs": pairs_payload,
        "candidates": candidates_payload,
        "rules": [
            "Consider device_type_id relevance (9=DC Combiner, 29=Tracker, "
            "30=DC Field)",
            "Prefer exact/semantically close matches in name_short/name_long",
            "If multiple plausible, pick the most specific",
            "Do NOT include explanations/rationales in the output",
        ],
        "output_schema": {
            "suggestions": [
                {
                    "index": 0,
                    "root_cause_id": 123,
                    "confidence": 0.8,
                }
            ]
        },
    }

    prompt_payload = {
        **user_prompt,
        "instruction": ("Call select_root_cause with your best suggestions only."),
    }
    system_content = [{"type": "input_text", "text": system_prompt}]
    user_content = [
        {
            "type": "input_text",
            "text": json.dumps(prompt_payload, ensure_ascii=False),
        }
    ]
    openai_input = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # Prefer tool function-calling; fall back to JSON-text parsing
    tools = [
        {
            "type": "function",
            "name": "select_root_cause",
            "description": ("Select best root cause per pair and return suggestions."),
            "parameters": {
                "type": "object",
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer"},
                                "root_cause_id": {
                                    "type": ["integer", "null"],
                                },
                                "confidence": {
                                    "type": ["number", "null"],
                                },
                            },
                            "required": [
                                "index",
                                "root_cause_id",
                                "confidence",
                            ],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["suggestions"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]

    try:
        resp = client.responses.create(
            model=request.model,
            tools=tools,  # type: ignore[arg-type]
            input=openai_input,  # type: ignore[arg-type]
        )
    except Exception as e:  # pragma: no cover - surface error details
        logger.exception("OpenAI responses.create failed")
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI error during responses.create: {str(e)}",
        )

    # Extract text for fallback parsing
    out_text = None
    try:
        out_text = getattr(resp, "output_text", None)
    except Exception:
        out_text = None
    if not out_text:
        try:
            out_text = getattr(resp, "model_dump_json", lambda: "{}")()
        except Exception:
            out_text = None

    suggestions: list[SuggestedRootCause] = []
    # Parse function_call outputs first
    try:
        outputs = getattr(resp, "output", [])
        for item in outputs or []:
            try:
                # Handle ResponseFunctionToolCall objects
                if hasattr(item, "type") and item.type == "function_call":
                    if item.name != "select_root_cause":
                        continue
                    args = item.arguments
                    if not args:
                        continue
                    parsed = args if isinstance(args, dict) else json.loads(args)
                # Handle dict format
                elif item.get("type") == "function_call":
                    name = item.get("name") or item.get("function", {}).get("name")
                    if name != "select_root_cause":
                        continue
                    args = item.get("arguments")
                    if not args and item.get("function"):
                        args = item["function"].get("arguments")
                    if not args:
                        continue
                    parsed = args if isinstance(args, dict) else json.loads(args)
                else:
                    continue
                raw = parsed.get("suggestions", [])
                for rc in raw:
                    try:
                        suggestions.append(
                            SuggestedRootCause(
                                index=int(rc.get("index")),
                                root_cause_id=(
                                    int(rc["root_cause_id"])
                                    if rc.get("root_cause_id") is not None
                                    else None
                                ),
                                confidence=(
                                    float(rc["confidence"])
                                    if rc.get("confidence") is not None
                                    else None
                                ),
                                rationale=None,
                            )
                        )
                    except Exception:
                        continue
                if suggestions:
                    break
            except Exception:
                continue
    except Exception:
        suggestions = []

    # Fallback: robust text parsing path
    if not suggestions:
        text = None
        try:
            text = getattr(resp, "output_text", None)
        except Exception:
            text = None
        if not text:
            try:
                outputs = getattr(resp, "output", [])
                if outputs and outputs[0].get("content"):
                    parts = outputs[0]["content"]
                    for part in parts:
                        ok = part.get("type") in ("output_text", "text")
                        if ok and part.get("text"):
                            text = part["text"]
                            break
            except Exception:
                text = None
        if not text:
            try:
                text = getattr(resp, "model_dump_json", lambda: "{}")()
            except Exception:
                text = "{}"
            logger.warning("OpenAI response had no text content; using fallback json")

        try:
            data = json.loads(text or "{}")
            raw = data.get("suggestions", [])
            for item in raw:
                try:
                    suggestions.append(
                        SuggestedRootCause(
                            index=int(item.get("index")),
                            root_cause_id=(
                                int(item["root_cause_id"])
                                if item.get("root_cause_id") is not None
                                else None
                            ),
                            confidence=(
                                float(item["confidence"])
                                if item.get("confidence") is not None
                                else None
                            ),
                            rationale=None,
                        )
                    )
                except Exception:
                    continue
        except Exception as e:
            logger.exception("Failed to parse JSON from OpenAI response: %s", e)

            try:
                if text:
                    match = re.search(r"\{[\s\S]*\}", text)
                    if match:
                        data = json.loads(match.group(0))
                        raw = data.get("suggestions", [])
                        for item in raw:
                            try:
                                suggestions.append(
                                    SuggestedRootCause(
                                        index=int(item.get("index")),
                                        root_cause_id=(
                                            int(item["root_cause_id"])
                                            if item.get("root_cause_id") is not None
                                            else None
                                        ),
                                        confidence=(
                                            float(item["confidence"])
                                            if item.get("confidence") is not None
                                            else None
                                        ),
                                        rationale=None,
                                    )
                                )
                            except Exception:
                                continue
            except Exception as e2:
                logger.debug("Regex-based JSON extraction failed: %s", str(e2))

    # Ensure all indexes are present in order
    if not suggestions:
        suggestions = [
            SuggestedRootCause(
                index=i,
                root_cause_id=None,
                confidence=None,
                rationale=None,
            )
            for i in range(len(pairs_payload))
        ]

    return SuggestRootCauseResponse(suggestions=suggestions)
