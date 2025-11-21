import json
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_user_data_async
from app.interfaces import UserData
from app.logger import logger

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional import surface
    OpenAI = None  # type: ignore


router = APIRouter(prefix="/ai", tags=["ai"])


class EventData(BaseModel):
    """Event information for AI analysis."""

    device_type_name: str
    count: int
    revenue_loss: float
    status: str  # 'open' or 'closed'


class DailyPerformanceStats(BaseModel):
    """Statistics for daily performance analysis."""

    project_name: str
    date: str
    actual_energy_mwh: float
    expected_energy_mwh: float
    budgeted_energy_mwh: float
    energy_difference_mwh: float
    energy_performance_percent: float
    trailing_30_day_actual: float
    trailing_30_day_budgeted: float
    trailing_30_day_difference: float
    trailing_30_day_performance_percent: float
    # Performance Index and Curtailment
    performance_index: float
    curtailment_mwh: float
    # Revenue data
    daily_revenue: float
    mtd_revenue: float
    # Events data
    events: list[EventData]
    total_events: int
    open_events: int
    closed_events: int
    total_revenue_loss: float


class DailyPerformanceSummaryRequest(BaseModel):
    """Request for daily performance summary generation."""

    stats: DailyPerformanceStats
    model: str = Field(default="gpt-4o-mini")


class DailyPerformanceSummaryResponse(BaseModel):
    """Response containing AI-generated performance summary."""

    summary: str


@router.post(
    "/daily-performance-summary",
    response_model=DailyPerformanceSummaryResponse,
)
async def generate_daily_performance_summary(
    *,
    request: DailyPerformanceSummaryRequest,
    user_data: Annotated[UserData, Depends(get_user_data_async)],
):
    """Generate an AI-written summary of daily project performance.

    Uses OpenAI to analyze key performance metrics and provide a written
    summary of the project's performance for the selected day.
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

    # Build the prompt with performance data
    system_prompt = (
        "You are an expert solar energy analyst. Generate a concise, "
        "professional summary of a solar project's daily performance. "
        "Focus on Performance Index (actual vs expected energy) and expected "
        "energy as the primary metrics. Do not mention budgeted energy. "
        "Keep the summary to 2-3 sentences maximum."
    )

    user_prompt = {
        "task": "analyze_daily_performance",
        "project_name": request.stats.project_name,
        "date": request.stats.date,
        "daily_metrics": {
            "actual_energy_mwh": request.stats.actual_energy_mwh,
            "expected_energy_mwh": request.stats.expected_energy_mwh,
            "performance_index": request.stats.performance_index,
            "curtailment_mwh": request.stats.curtailment_mwh,
        },
        "trailing_30_day_metrics": {
            "actual_energy_mwh": request.stats.trailing_30_day_actual,
            "budgeted_energy_mwh": request.stats.trailing_30_day_budgeted,
            "energy_difference_mwh": request.stats.trailing_30_day_difference,
            "performance_percent": request.stats.trailing_30_day_performance_percent,
        },
        "revenue_metrics": {
            "daily_revenue": request.stats.daily_revenue,
            "mtd_revenue": request.stats.mtd_revenue,
        },
        "events_summary": {
            "total_events": request.stats.total_events,
            "open_events": request.stats.open_events,
            "closed_events": request.stats.closed_events,
            "total_revenue_loss": request.stats.total_revenue_loss,
            "events_by_device_type": [
                {
                    "device_type": event.device_type_name,
                    "count": event.count,
                    "revenue_loss": event.revenue_loss,
                    "status": event.status,
                }
                for event in request.stats.events
            ],
        },
        "instructions": [
            "Focus on the Performance Index (actual vs expected energy) as the primary metric",
            "Highlight the expected energy and how actual generation compares to it",
            "Mention the 30-day trailing performance trend",
            "Include revenue impact and any significant events affecting performance",
            "Note any open events that may be impacting generation",
            "Mention curtailment if present",
            "Do NOT mention budgeted energy comparisons",
            "Use professional, technical language appropriate for energy analysts",
            "Be specific about percentages, energy values, and revenue impact",
            "Keep the tone informative but concise",
        ],
    }

    system_content = [{"type": "input_text", "text": system_prompt}]
    user_content = [
        {
            "type": "input_text",
            "text": json.dumps(user_prompt, ensure_ascii=False),
        }
    ]
    openai_input = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # Use function calling for structured response
    tools = [
        {
            "type": "function",
            "name": "generate_performance_summary",
            "description": "Generate a professional performance summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A concise 2-3 sentence summary of the project's daily performance",
                    },
                },
                "required": ["summary"],
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

    # Extract the summary from the response
    summary = "Unable to generate performance summary at this time."

    try:
        outputs = getattr(resp, "output", [])
        for item in outputs or []:
            try:
                # Handle ResponseFunctionToolCall objects
                if hasattr(item, "type") and item.type == "function_call":
                    if item.name != "generate_performance_summary":
                        continue
                    args = item.arguments
                    if not args:
                        continue
                    parsed = args if isinstance(args, dict) else json.loads(args)
                    summary = parsed.get("summary", summary)
                    break
                # Handle dict format
                elif item.get("type") == "function_call":
                    name = item.get("name") or item.get("function", {}).get("name")
                    if name != "generate_performance_summary":
                        continue
                    args = item.get("arguments")
                    if not args and item.get("function"):
                        args = item["function"].get("arguments")
                    if not args:
                        continue
                    parsed = args if isinstance(args, dict) else json.loads(args)
                    summary = parsed.get("summary", summary)
                    break
            except Exception:
                continue
    except Exception:
        # Fallback to text parsing
        try:
            text = getattr(resp, "output_text", None)
            if text:
                data = json.loads(text)
                summary = data.get("summary", summary)
        except Exception:
            logger.warning("Failed to parse OpenAI response, using fallback summary")

    return DailyPerformanceSummaryResponse(summary=summary)
