import json
import logging
import os
import statistics
from typing import Any, TypedDict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional import surface
    OpenAI = None  # type: ignore


router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


class ConversationMessage(BaseModel):
    """A message in the conversation history."""

    role: str  # 'user' or 'assistant'
    content: str


class TimeseriesData(BaseModel):
    """Timeseries data structure matching the API response format."""

    index: list[str]  # timestamps
    unit: dict[str, str]  # column_name -> unit
    data: dict[str, list[float | None]]  # column_name -> values


class SCADADataPoint(BaseModel):
    """SCADA data point structure."""

    sensor_type_id: int
    sensor_type_name: str | None = None
    unit: str | None = None
    x: list[str]  # timestamps
    y: list[float | None]  # values


class BatterySettlementAnalysisRequest(BaseModel):
    """Request for battery settlement analysis."""

    project_id: str
    project_name: str | None = None
    start: str  # ISO format datetime
    end: str  # ISO format datetime
    qse_data: TimeseriesData | None = None
    calculated_data: TimeseriesData | None = None
    scada_data: list[SCADADataPoint] | None = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    user_message: str | None = None
    model: str = Field(default="gpt-4o")


class BatterySettlementAnalysisResponse(BaseModel):
    """todo"""

    content: str


class ColumnStats(TypedDict):
    """todo"""

    count: int
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    std: float | None
    sum: float | None
    unit: str


def _aggregate_timeseries_stats(*, data: TimeseriesData) -> dict[str, ColumnStats]:
    """Aggregate timeseries data into statistical summaries.

        Returns dict of {column_name: {stat_name: value}}

    Args:
        data: TODO: describe.
    """
    stats: dict[str, ColumnStats] = {}
    for col_name, values in data.data.items():
        # Filter out None values
        numeric_values = [v for v in values if v is not None]
        if not numeric_values:
            stats[col_name] = {
                "count": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "std": None,
                "sum": None,
                "unit": data.unit.get(col_name, ""),
            }
            continue

        # Calculate statistics
        stats[col_name] = {
            "count": len(numeric_values),
            "mean": statistics.mean(numeric_values),
            "median": statistics.median(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values),
            "std": (
                statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
            ),
            "sum": sum(numeric_values),
            "unit": data.unit.get(col_name, ""),
        }

    return stats


def _estimate_token_count(*, data: Any) -> int:
    """Rough estimate of token count for data.

    Args:
        data: TODO: describe.
    """
    json_str = json.dumps(data)
    # Rough estimate: ~4 characters per token
    return len(json_str) // 4


def _prepare_data_for_llm(
    *, request: BatterySettlementAnalysisRequest
) -> dict[str, Any]:
    """Prepare data for LLM, aggregating if necessary to stay under token limits.

    Args:
        request: TODO: describe.
    """
    prepared_data: dict[str, Any] = {
        "project_id": request.project_id,
        "project_name": request.project_name,
        "time_range": {"start": request.start, "end": request.end},
    }

    # Estimate total token count
    qse_tokens = (
        _estimate_token_count(data=request.qse_data.model_dump())
        if request.qse_data
        else 0
    )
    calc_tokens = (
        _estimate_token_count(data=request.calculated_data.model_dump())
        if request.calculated_data
        else 0
    )
    scada_tokens = (
        _estimate_token_count(data=[s.model_dump() for s in request.scada_data])
        if request.scada_data
        else 0
    )
    total_tokens = qse_tokens + calc_tokens + scada_tokens

    logger.info(
        f"Estimated tokens - QSE: {qse_tokens}, "
        f"Calc: {calc_tokens}, SCADA: {scada_tokens}, Total: {total_tokens}"
    )

    # If total is reasonable (<50k tokens), send raw data
    if total_tokens < 50000:
        if request.qse_data:
            prepared_data["qse_data"] = request.qse_data.model_dump()
        if request.calculated_data:
            prepared_data["calculated_data"] = request.calculated_data.model_dump()
        if request.scada_data:
            prepared_data["scada_data"] = [s.model_dump() for s in request.scada_data]
    else:
        # Aggregate to statistical summaries
        logger.info("Aggregating data to reduce token count")
        if request.qse_data:
            prepared_data["qse_data_stats"] = _aggregate_timeseries_stats(
                data=request.qse_data
            )
            prepared_data["qse_data_point_count"] = len(request.qse_data.index)

        if request.calculated_data:
            prepared_data["calculated_data_stats"] = _aggregate_timeseries_stats(
                data=request.calculated_data
            )
            prepared_data["calculated_data_point_count"] = len(
                request.calculated_data.index
            )

        if request.scada_data:
            scada_stats = []
            for sensor_data in request.scada_data:
                numeric_values = [v for v in sensor_data.y if v is not None]
                if numeric_values:
                    scada_stats.append(
                        {
                            "sensor_type_id": sensor_data.sensor_type_id,
                            "sensor_type_name": sensor_data.sensor_type_name,
                            "unit": sensor_data.unit,
                            "count": len(numeric_values),
                            "mean": statistics.mean(numeric_values),
                            "median": statistics.median(numeric_values),
                            "min": min(numeric_values),
                            "max": max(numeric_values),
                            "std": (
                                statistics.stdev(numeric_values)
                                if len(numeric_values) > 1
                                else 0.0
                            ),
                        }
                    )
            prepared_data["scada_data_stats"] = scada_stats

    return prepared_data


@router.post(
    "/battery-settlement-analysis", response_model=BatterySettlementAnalysisResponse
)
async def analyze_battery_settlement(
    *,
    request: BatterySettlementAnalysisRequest,
):
    """Analyze battery settlement data using AI and return a single formatted text.

    Args:
        request: TODO: describe.
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

    # Prepare data for LLM
    prepared_data = _prepare_data_for_llm(request=request)

    # Build system prompt
    system_prompt = """You are Aria, an expert energy storage analyst specializing
in battery energy storage systems (BESS) and electricity market operations.
Your role is to analyze battery settlement data and provide comprehensive,
technical insights.

When analyzing battery performance data, you should:

1. Performance Analysis: Evaluate the battery's operational efficiency,
   including:
   - Round-trip efficiency and energy throughput
   - Charging and discharging patterns
   - Capacity utilization and cycling behavior

2. Market & Financial Analysis: Assess arbitrage opportunities and revenue
   generation:
   - Price spread analysis between Real-Time (RT) and Day-Ahead (DA) markets
   - Revenue optimization and profitability metrics
   - Imbalance charges and settlement impacts
   - Net profit trends and cumulative revenue

3. Operational Insights: Identify operational patterns and anomalies:
   - Optimal dispatch times based on market signals
   - Deviations between forecasted and actual positions
   - Unusual behavior or performance degradation
   - Response to price signals

4. Technical Recommendations: Provide actionable insights:
   - Opportunities for improved market participation
   - Potential operational optimizations
   - Risk factors or areas of concern
   - Strategic recommendations for future operations

Be specific with numbers, percentages, and data-driven conclusions. Use
technical terminology appropriate for energy analysts and asset managers.
Focus on insights that drive operational and financial decisions."""

    # Build messages
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    for msg in request.conversation_history:
        messages.append({"role": msg.role, "content": msg.content})

    if request.user_message:
        user_content = request.user_message
    else:
        user_content = (
            f"Please analyze the following battery settlement data for "
            f"{request.project_name or 'the project'} "
            f"from {request.start} to {request.end}.\n\n"
            f"Data:\n{json.dumps(prepared_data, indent=2)}\n\n"
            f"Provide a comprehensive technical analysis of the battery's "
            f"performance, market participation, and financial outcomes."
        )

    messages.append({"role": "user", "content": user_content})

    try:
        resp = client.chat.completions.create(
            model=request.model,
            messages=messages,  # type: ignore
            temperature=0.7,
            max_tokens=4000,
        )
    except Exception as e:
        logger.exception("OpenAI chat.completions.create failed")
        raise HTTPException(status_code=502, detail=f"OpenAI error: {str(e)}")

    content = ""
    try:
        if resp.choices and len(resp.choices) > 0:
            message = resp.choices[0].message
            content = getattr(message, "content", None) or ""
    except Exception:
        content = (
            getattr(resp, "choices", [{}])[0].get("message", {}).get("content", "")
            or ""
        )

    if not content:
        content = "Unable to generate analysis at this time. Please try again later."

    return BatterySettlementAnalysisResponse(content=content)
