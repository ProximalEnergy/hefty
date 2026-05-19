import json
import os
from datetime import datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

import pandas as pd
from core.crud.operational.cmms_permissions import (
    get_cmms_permissions_by_project_id as core_get_cmms_permissions_by_project_id,
)
from core.crud.operational.projects import get_project
from core.crud.project.cmms_tickets import get_project_cmms_tickets
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import interfaces
from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed
from app.logger import get_logger

logger = get_logger(name=__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional import surface
    OpenAI = None  # type: ignore


router = APIRouter(prefix="/ai", tags=["ai"])

_UPDATE_LIKE_KEYS = frozenset(
    {
        "comment",
        "comments",
        "notes",
        "note",
        "description",
        "text",
        "message",
        "memo",
        "details",
        "resolution",
        "worknote",
        "work_note",
        "status_comment",
        "activity",
        "summary",
    }
)


def _dt_iso_for_prompt(*, value: Any) -> str | None:
    """Normalize pandas/sql timestamps for JSON prompt output.

    Args:
        value: Datetime-like or NaN sentinel from a dataframe row.

    Returns:
        ISO string when valid, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return None


def _build_site_location_context(
    *,
    location: Any,
    cmms_device_name: Any,
    cmms_device_id: Any,
) -> str | None:
    """Combine CMMS location / equipment fields for on-site context.

    Args:
        location: CMMS location label (e.g. block or area).
        cmms_device_name: Provider device label (often includes inverter/string).
        cmms_device_id: Provider device identifier.

    Returns:
        Short combined string for the model, or None if empty.
    """
    parts: list[str] = []
    for label, val in (
        ("Site location", location),
        ("Equipment / asset", cmms_device_name),
        ("Provider device id", cmms_device_id),
    ):
        if val is None:
            continue
        if isinstance(val, float) and pd.isna(val):
            continue
        s = str(val).strip()
        if s:
            parts.append(f"{label}: {s}")
    return " · ".join(parts) if parts else None


def _extract_updates_from_json_raw(*, raw: Any, max_chars: int = 900) -> str | None:
    """Best-effort pull of comment/history text from provider-specific payloads.

    Args:
        raw: Parsed json_raw object (usually a dict).
        max_chars: Cap on returned text.

    Returns:
        Concatenated update hints or None.
    """
    if not isinstance(raw, dict):
        return None
    chunks: list[str] = []

    def add_str(*, prefix: str, s: str) -> None:
        t = s.strip()
        if t:
            chunks.append(f"{prefix}: {t}")

    for key in (
        "comments",
        "work_order_notes",
        "notes",
        "description",
        "long_description",
        "last_comment",
        "resolution_notes",
        "resolution",
        "problem_description",
    ):
        val = raw.get(key)
        if isinstance(val, str):
            add_str(prefix=key, s=val)

    for hist_key in ("history", "workOrderHistory", "activities", "audit", "timeline"):
        hist = raw.get(hist_key)
        if not isinstance(hist, list) or not hist:
            continue
        tail = hist[-3:]
        for item in tail:
            if not isinstance(item, dict):
                continue
            bits: list[str] = []
            for k, v in item.items():
                lk = str(k).lower()
                if any(u in lk for u in _UPDATE_LIKE_KEYS):
                    if isinstance(v, str) and v.strip():
                        bits.append(v.strip())
                    elif v is not None and not isinstance(v, (dict, list)):
                        bits.append(str(v).strip())
            st = item.get("status") or item.get("status_name")
            if isinstance(st, str) and st.strip():
                bits.append(f"status {st.strip()}")
            if bits:
                chunks.append(f"[{hist_key}] " + " — ".join(bits))

    if not chunks:
        return None
    out = " ".join(chunks)
    if len(out) > max_chars:
        return out[:max_chars] + "…"
    return out


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
    project_id: UUID | None = None
    cmms_period_start: datetime | None = None
    cmms_period_end: datetime | None = None


class DailyPerformanceSummaryRequest(BaseModel):
    """Request for daily performance summary generation."""

    stats: DailyPerformanceStats
    model: str = Field(default="gpt-5-mini")


class DailyPerformanceSummaryResponse(BaseModel):
    """Response containing AI-generated performance summary."""

    summary: str
    cmms_tickets_activity: str | None = None


# Longest typical local calendar day (~25h on DST fall-back); above this ⇒
# multi-day window (two+ local midnights spanned).
_MULTI_DAY_MIN_ABSOLUTE_SPAN = timedelta(hours=27)
# When CMMS bounds are missing, treat these as range separators (not bare "-"
# in YYYY-MM-DD).
_RANGE_LABEL_SEPARATORS = (" – ", " — ", " to ", " - ")


def _infer_report_kind(*, stats: DailyPerformanceStats) -> str:
    """Classify report window as single-day vs multi-day for the model prompt.

    Args:
        stats: Client-submitted performance stats.

    Returns:
        Label for the user prompt ``report_kind`` field.
    """
    start = stats.cmms_period_start
    end = stats.cmms_period_end
    if start is not None and end is not None and end > start:
        if (end - start) > _MULTI_DAY_MIN_ABSOLUTE_SPAN:
            return "multi-day (e.g. weekly) range"
        return "single day"
    label = stats.date
    if any(sep in label for sep in _RANGE_LABEL_SEPARATORS):
        return "multi-day (e.g. weekly) range"
    return "single day"


async def _load_cmms_ticket_prompt_rows(
    *,
    user: interfaces.UserAuthed,
    project_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> tuple[list[dict[str, Any]], bool]:
    """Load CMMS tickets for the Aria summary prompt.

    Selects tickets whose source_created_at falls from seven days before
    period_start through period_end (inclusive).

    Args:
        user: Authenticated user (access check).
        project_id: Project scope for CMMS data.
        period_start: Report window start (inclusive).
        period_end: Report window end (inclusive).

    Returns:
        Sanitized ticket dicts for the model and whether CMMS is configured.
    """
    if project_id not in user.operational_project_ids:
        raise HTTPException(status_code=403, detail="Forbidden")
    project_row = await get_project(project_id=project_id).get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    if project_row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    name_short = project_row.name_short

    cmms_permissions = await core_get_cmms_permissions_by_project_id(
        company_id=user.company_id,
        project_id=project_id,
        can_view=True,
    ).get_async(output_type=OutputType.PANDAS)
    if cmms_permissions.empty:
        return [], False

    cmms_integration_ids = cmms_permissions["cmms_integration_id"].unique().tolist()
    pad_start = period_start - timedelta(days=7)
    pad_end = period_end
    cmms_df = await get_project_cmms_tickets(
        cmms_integration_ids=cmms_integration_ids,
        source_created_at_start=pad_start,
        source_created_at_end=pad_end,
        max_results=10,
        include_json_raw=True,
        source_created_order_asc=True,
    ).get_async(schema=name_short, output_type=OutputType.PANDAS)

    if cmms_df.empty:
        return [], True

    provider_info = cmms_permissions[
        ["cmms_integration_id", "cmms_provider_name_long"]
    ].drop_duplicates()
    merged = cmms_df.merge(provider_info, on="cmms_integration_id", how="left")

    rows: list[dict[str, Any]] = []
    for rec in cast(list[dict[str, Any]], merged.to_dict(orient="records")):
        raw = rec.get("json_raw")
        if raw is not None and isinstance(raw, float) and pd.isna(raw):
            raw = None
        raw_str: str | None
        if raw is None:
            raw_str = None
        else:
            raw_str = json.dumps(raw, default=str, ensure_ascii=False)
            if len(raw_str) > 4200:
                raw_str = raw_str[:4200] + "…"
        created = rec.get("source_created_at")
        if created is not None and isinstance(created, float) and pd.isna(created):
            created = None
        inferred_updates = _extract_updates_from_json_raw(raw=raw)
        site_ctx = _build_site_location_context(
            location=rec.get("location"),
            cmms_device_name=rec.get("cmms_device_name"),
            cmms_device_id=rec.get("cmms_device_id"),
        )
        rows.append(
            {
                "key": rec.get("key"),
                "source_created_at": _dt_iso_for_prompt(value=created),
                "status": rec.get("status"),
                "status_change_at": _dt_iso_for_prompt(
                    value=rec.get("status_change_at"),
                ),
                "due_date": _dt_iso_for_prompt(value=rec.get("due_date")),
                "priority": rec.get("priority"),
                "assigned_to": rec.get("assigned_to"),
                "reporter": rec.get("reporter"),
                "site_location_context": site_ctx,
                "location": rec.get("location"),
                "cmms_device_name": rec.get("cmms_device_name"),
                "cmms_device_id": rec.get("cmms_device_id"),
                "summary": rec.get("summary"),
                "summary_long": rec.get("summary_long"),
                "latest_updates_in_payload": inferred_updates,
                "proximal_record_updated_at": _dt_iso_for_prompt(
                    value=rec.get("db_updated_at"),
                ),
                "cmms_provider_name_long": rec.get("cmms_provider_name_long"),
                "link": rec.get("link"),
                "json_raw_excerpt": raw_str,
            }
        )
    return rows, True


@router.post(
    "/daily-performance-summary",
    response_model=DailyPerformanceSummaryResponse,
)
async def generate_daily_performance_summary(
    *,
    request: DailyPerformanceSummaryRequest,
    user: Annotated[UserAuthed, Depends(get_user)],
):
    """Generate an AI-written summary of daily project performance.

        Uses OpenAI to analyze key performance metrics and provide a written
        summary of the project's performance for the selected day.

    Args:
        request: Performance stats and optional CMMS window for ticket context.
        user: Authenticated user (for CMMS access).
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

    cmms_tickets: list[dict[str, Any]] = []
    cmms_integration_configured = False
    stats = request.stats
    request_has_cmms_window = (
        stats.project_id is not None
        and stats.cmms_period_start is not None
        and stats.cmms_period_end is not None
    )
    if request_has_cmms_window:
        pid = stats.project_id
        p_start = stats.cmms_period_start
        p_end = stats.cmms_period_end
        if pid is None or p_start is None or p_end is None:
            raise HTTPException(
                status_code=400,
                detail="CMMS window requires project_id and period bounds.",
            )
        cmms_tickets, cmms_integration_configured = await _load_cmms_ticket_prompt_rows(
            user=user,
            project_id=pid,
            period_start=p_start,
            period_end=p_end,
        )

    report_kind = _infer_report_kind(stats=request.stats)

    system_prompt = (
        "You are an expert solar energy analyst writing the Aria Performance "
        "Summary for asset managers. Produce clear, scannable text: short "
        "paragraphs, no markdown headings, no bullet lists unless essential. "
        "For performance: lead with Performance Index (actual vs expected), "
        "then generation vs expected MWh, trailing trend, revenue, "
        "curtailment if material, and notable operational events. "
        "Do not mention budgeted energy. "
        "For CMMS: each ticket includes site_location_context, status, "
        "status_change_at, due_date, summaries, latest_updates_in_payload "
        "(when extractable from json_raw), and json_raw_excerpt. "
        "Always cite on-site placement when data allows: quote location, "
        "equipment / inverter / block / string identifiers from "
        "site_location_context, cmms_device_name, location, or json_raw. "
        "Per ticket, mention current status, when status last changed if "
        "known, due date if relevant, and brief substance from summaries "
        "plus latest_updates_in_payload. "
        "If cmms_integration_configured is false, say CMMS data was not "
        "available. If no tickets in window, say none synced. "
        "Use one or two compact paragraphs; separate distinct tickets with "
        "clear sentences (no bullet lists)."
    )

    user_prompt: dict[str, Any] = {
        "task": "analyze_daily_performance",
        "report_kind": report_kind,
        "project_name": request.stats.project_name,
        "date_or_range_label": request.stats.date,
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
        "cmms": {
            "cmms_context_requested": request_has_cmms_window,
            "cmms_integration_configured": cmms_integration_configured,
            "ticket_count": len(cmms_tickets),
            "tickets": cmms_tickets,
        },
        "instructions": [
            "performance_summary: 3–5 short sentences, plain sentences only",
            "cmms_tickets_activity: name ticket keys; for each, lead with "
            "on-site location/equipment (block/inverter/etc. when present), "
            "then status and latest update timing, then work summary; "
            "if no CMMS window requested, say CMMS ticket lookup was not run",
            "Use numbers from the payload; round sensibly",
            "Do NOT mention budgeted energy comparisons",
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

    tools = [
        {
            "type": "function",
            "name": "generate_aria_performance_summary",
            "description": (
                "Generate the Aria performance narrative and CMMS activity paragraph."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "performance_summary": {
                        "type": "string",
                        "description": (
                            "Performance narrative: PI, energy vs expected, "
                            "trailing trend, revenue, events, curtailment."
                        ),
                    },
                    "cmms_tickets_activity": {
                        "type": "string",
                        "description": (
                            "CMMS narrative: per ticket, cite site location "
                            "/ equipment (block, inverter #, etc.), status, "
                            "status timing / latest updates, and issue summary."
                        ),
                    },
                },
                "required": ["performance_summary", "cmms_tickets_activity"],
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

    summary = "Unable to generate performance summary at this time."
    cmms_activity: str | None = None

    try:
        outputs = getattr(resp, "output", [])
        for item in outputs or []:
            try:
                if hasattr(item, "type") and item.type == "function_call":
                    if item.name != "generate_aria_performance_summary":
                        continue
                    args = item.arguments
                    if not args:
                        continue
                    parsed_obj = args if isinstance(args, dict) else json.loads(args)
                    parsed: dict[str, Any] = cast(dict[str, Any], parsed_obj)
                    summary = parsed.get("performance_summary") or parsed.get(
                        "summary",
                        summary,
                    )
                    cmms_activity = parsed.get("cmms_tickets_activity")
                    break
                elif isinstance(item, dict) and item.get("type") == "function_call":
                    name = item.get("name") or item.get("function", {}).get("name")
                    if name != "generate_aria_performance_summary":
                        continue
                    args = item.get("arguments")
                    if not args and item.get("function"):
                        args = item["function"].get("arguments")
                    if not args:
                        continue
                    parsed2 = args if isinstance(args, dict) else json.loads(args)
                    parsed_dict: dict[str, Any] = cast(dict[str, Any], parsed2)
                    summary = parsed_dict.get("performance_summary") or parsed_dict.get(
                        "summary",
                        summary,
                    )
                    cmms_activity = parsed_dict.get("cmms_tickets_activity")
                    break
            except Exception:
                continue
    except Exception:
        try:
            text = getattr(resp, "output_text", None)
            if text:
                data = json.loads(text)
                summary = data.get("performance_summary", data.get("summary", summary))
                cmms_activity = data.get("cmms_tickets_activity")
        except Exception:
            logger.warning("Failed to parse OpenAI response, using fallback summary")

    return DailyPerformanceSummaryResponse(
        summary=summary,
        cmms_tickets_activity=cmms_activity,
    )
