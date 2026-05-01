"""AI-assisted extraction of historical warranty claim fields from uploaded PDFs."""

import datetime
import json
from typing import Annotated, Any
from uuid import UUID

from core.crud.operational.failure_modes import get_failure_modes
from core.crud.project import events as core_events
from core.db_query import OutputType
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import dependencies
from app.dependencies import get_project_name_short_async
from app.logger import logger
from app.v1.ai._openai_helpers import (
    build_openai_responses_client,
    extract_response_tool_json,
)

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_FILES = 10
DEFAULT_MODEL = "gpt-5.4-mini"

CLAIM_STATUS_VALUES = ["draft", "submitted", "in_progress", "resolved", "closed"]
CLAIM_UPDATE_TYPE_VALUES = [
    "status_change",
    "submission",
    "oem_message",
    "note",
    "parts",
    "field_visit",
]


class ConfigOption(BaseModel):
    """Existing claim config the LLM can pick from."""

    claim_config_id: int
    counterparty_name: str | None = None


class DeviceOption(BaseModel):
    """Project device the LLM can match against."""

    device_id: int
    device_name: str | None = None
    device_type_id: int | None = None
    device_type_name: str | None = None


class DeviceTypeOption(BaseModel):
    """Device type the LLM can pick when no specific device matches."""

    device_type_id: int
    device_type_name: str


class HistoricalClaimContext(BaseModel):
    """Context describing the project to help the LLM."""

    project_id: UUID | None = None
    project_name: str = ""
    company_name: str = ""
    claim_configs: list[ConfigOption] = Field(default_factory=list)
    devices: list[DeviceOption] = Field(default_factory=list)
    device_types: list[DeviceTypeOption] = Field(default_factory=list)


class ExtractedDevice(BaseModel):
    """Suggested device row for the historical claim."""

    device_id: int | None = None
    device_type_id: int | None = None
    device_name_hint: str = ""
    oem_serial_number: str = ""
    oem_part_number: str = ""
    notes: str = ""
    event_id: int | None = None


class ExtractedUpdate(BaseModel):
    """Suggested timeline update for the historical claim."""

    update_type: str
    message: str = ""
    occurred_at: datetime.datetime | None = None
    from_status: str | None = None
    to_status: str | None = None


class CandidateEvent(BaseModel):
    """An event that could be linked to a claim device row."""

    event_id: int
    device_id: int
    time_start: datetime.datetime
    time_end: datetime.datetime | None = None
    failure_mode: str | None = None


class HistoricalClaimExtractResponse(BaseModel):
    """Structured suggestions for populating a historical warranty claim."""

    claim_config_id: int | None = None
    oem_name_suggested: str | None = None
    summary: str = ""
    external_reference: str | None = None
    status: str = "closed"
    claim_date: datetime.date | None = None
    devices: list[ExtractedDevice] = Field(default_factory=list)
    updates: list[ExtractedUpdate] = Field(default_factory=list)
    device_event_candidates: dict[int, list[CandidateEvent]] = Field(
        default_factory=dict,
    )


def _extract_tool_schema() -> dict[str, Any]:
    """Return the JSON schema for the extract_historical_claim tool.

    Returns:
        JSON Schema for OpenAI function tool parameters.
    """
    return {
        "type": "object",
        "properties": {
            "claim_config_id": {
                "type": ["integer", "null"],
                "description": (
                    "ID of the best-matching existing claim_config based on OEM. "
                    "Null if no existing config matches."
                ),
            },
            "oem_name_suggested": {
                "type": ["string", "null"],
                "description": (
                    "OEM / counterparty name as written on the claim form. "
                    "Null if a claim_config_id was selected."
                ),
            },
            "summary": {
                "type": "string",
                "description": (
                    "One or two sentence summary of the issue. "
                    "Use concrete device names and symptoms."
                ),
            },
            "external_reference": {
                "type": ["string", "null"],
                "description": (
                    "The OEM's identifier for THIS CLAIM as a whole "
                    "(e.g. claim number, case number, RMA number, ticket "
                    "number, ServiceNow ID, support ID). Usually labeled "
                    "'Case #', 'RMA #', 'Claim ID', 'Ticket #', etc. and "
                    "appears in email subjects/headers. "
                    "DO NOT use a device serial number, part number, model "
                    "number, lot number, firmware version, project ID, "
                    "purchase order number, or our internal claim number "
                    "here — those are not external references. "
                    "Null if no claim-level identifier is present."
                ),
            },
            "status": {
                "type": "string",
                "enum": CLAIM_STATUS_VALUES,
                "description": (
                    "Historical claim status. Use 'closed' for fully "
                    "finished/settled claims, 'resolved' when parts were "
                    "replaced but the claim is not formally closed, "
                    "'in_progress' if correspondence is ongoing, "
                    "'submitted' if only the form was sent."
                ),
            },
            "claim_date": {
                "type": ["string", "null"],
                "description": (
                    "ISO 8601 date (YYYY-MM-DD) the claim was filed with the "
                    "OEM, OR if not present, the date the underlying incident "
                    "/ failure occurred. Used to look up site events that "
                    "could be linked to the claim. Null if no usable date."
                ),
            },
            "devices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": ["integer", "null"],
                            "description": (
                                "Matching device_id from the provided devices "
                                "list. Null if no confident match."
                            ),
                        },
                        "device_type_id": {
                            "type": ["integer", "null"],
                            "description": (
                                "device_type_id of the impacted asset. Pick "
                                "from the provided device_types list "
                                "(or the device_type_id on the matched "
                                "device). Set this even when device_id is "
                                "null but the asset class is clear from the "
                                "PDFs (e.g. it's clearly a string inverter)."
                            ),
                        },
                        "device_name_hint": {
                            "type": "string",
                            "description": (
                                "The asset's site/SCADA name or position "
                                "tag — what we use internally to identify "
                                "the device — as referenced in the PDFs "
                                "(e.g. '1.1.1', 'INV-14', 'Block 3', "
                                "'PCS 2.1'). Should look like one of the "
                                "device_name values in the provided "
                                "devices list. Do NOT put the OEM model "
                                "name, brand, serial number, or part "
                                "number here — those have their own "
                                "fields. Empty string if no such tag is "
                                "mentioned."
                            ),
                        },
                        "oem_serial_number": {"type": "string"},
                        "oem_part_number": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                    "required": [
                        "device_id",
                        "device_type_id",
                        "device_name_hint",
                        "oem_serial_number",
                        "oem_part_number",
                        "notes",
                    ],
                    "additionalProperties": False,
                },
            },
            "updates": {
                "type": "array",
                "description": (
                    "Chronological timeline entries reconstructed from the "
                    "documents (form submission, OEM replies, site visits, "
                    "parts shipments, status changes)."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "update_type": {
                            "type": "string",
                            "enum": CLAIM_UPDATE_TYPE_VALUES,
                        },
                        "message": {"type": "string"},
                        "occurred_at": {
                            "type": ["string", "null"],
                            "description": (
                                "ISO 8601 timestamp of when the event "
                                "occurred. Null if unknown."
                            ),
                        },
                        "from_status": {
                            "type": ["string", "null"],
                            "enum": [*CLAIM_STATUS_VALUES, None],
                        },
                        "to_status": {
                            "type": ["string", "null"],
                            "enum": [*CLAIM_STATUS_VALUES, None],
                        },
                    },
                    "required": [
                        "update_type",
                        "message",
                        "occurred_at",
                        "from_status",
                        "to_status",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "claim_config_id",
            "oem_name_suggested",
            "summary",
            "external_reference",
            "status",
            "claim_date",
            "devices",
            "updates",
        ],
        "additionalProperties": False,
    }


def _suggest_events_tool_schema() -> dict[str, Any]:
    """JSON schema for the second-turn `suggest_claim_events` tool.

    Returns:
        JSON Schema for OpenAI function tool parameters.
    """
    return {
        "type": "object",
        "properties": {
            "device_events": {
                "type": "array",
                "description": (
                    "One entry per device row from the extracted claim. "
                    "Pick the single best matching event_id from the "
                    "candidates list provided for that row, or null when "
                    "no candidate clearly matches."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "row_index": {"type": "integer"},
                        "event_id": {"type": ["integer", "null"]},
                    },
                    "required": ["row_index", "event_id"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["device_events"],
        "additionalProperties": False,
    }


def _system_prompt(*, context: HistoricalClaimContext) -> str:
    """Build the system prompt for the LLM.

    Args:
        context: Project context provided by the frontend.

    Returns:
        Prompt string.
    """
    configs_json = json.dumps(
        [c.model_dump() for c in context.claim_configs],
        ensure_ascii=False,
    )
    devices_preview = context.devices[:400]
    devices_json = json.dumps(
        [d.model_dump() for d in devices_preview],
        ensure_ascii=False,
    )
    device_types_json = json.dumps(
        [dt.model_dump() for dt in context.device_types],
        ensure_ascii=False,
    )
    single_config = (
        context.claim_configs[0] if len(context.claim_configs) == 1 else None
    )
    oem_line = (
        (
            f"The user has already confirmed the OEM is "
            f"'{single_config.counterparty_name}' "
            f"(claim_config_id={single_config.claim_config_id}). "
            f"Always return that claim_config_id and leave "
            f"oem_name_suggested null. "
            f"The provided devices list has been pre-filtered to devices "
            f"manufactured by this OEM.\n\n"
        )
        if single_config is not None
        else ""
    )
    return (
        "You extract structured warranty claim data from one or more PDFs "
        "a user is filing as a HISTORICAL claim (the claim has already been "
        "submitted and possibly resolved before being entered into this "
        "system). "
        f"Project name: {context.project_name}. "
        f"Submitter company: {context.company_name}. "
        "The PDFs usually include: (1) the warranty claim form that was "
        "submitted to the OEM, and (2) printed email correspondence with "
        "the OEM. Extract data that reflects how the claim should be stored "
        "in the database.\n\n"
        f"{oem_line}"
        "Existing claim_configs (OEM options) for this project:\n"
        f"{configs_json}\n\n"
        "Device types in this project:\n"
        f"{device_types_json}\n\n"
        "Project devices (subset, with device_type_id and device_type_name):\n"
        f"{devices_json}\n\n"
        "Rules:\n"
        "- Prefer an existing claim_config_id over suggesting a new OEM name. "
        "Only set oem_name_suggested when none of the existing configs match.\n"
        "- For devices, match by device name/tag to the provided devices list "
        "and fill device_id when confident; always include the "
        "device_name_hint from the PDFs so the user can verify.\n"
        "- device_name_hint must be the asset's site/SCADA tag as written "
        "in the PDFs (e.g. '1.1.1', 'INV-14', 'Block 3') — it should look "
        "like the device_name values in the provided devices list. Never "
        "put the OEM model name, brand, serial, or part number here; those "
        "belong in oem_serial_number / oem_part_number / notes.\n"
        "- Always set device_type_id when the asset class is identifiable "
        "from the PDFs (e.g. clearly a string inverter, transformer, BESS "
        "PCS, etc.) — even when device_id is null. When device_id is set, "
        "device_type_id must equal that device's device_type_id.\n"
        "- external_reference is the OEM's identifier for the CLAIM ITSELF "
        "(case #, RMA #, ticket #, claim ID, support ID), typically issued "
        "by the OEM and visible in email subjects or 'Case Number:' fields. "
        "Never put a device serial number, part number, model number, lot "
        "number, firmware version, project ID, PO number, or our own "
        "internal claim number into external_reference. Device serial / part "
        "numbers go on the device row (oem_serial_number / oem_part_number). "
        "If no claim-level identifier exists, return null.\n"
        "- Use '' (empty string) when a text field is unknown. Use null only "
        "where the schema allows it.\n"
        "- Reconstruct timeline updates in chronological order. The first "
        "update should typically be 'submission' when the form was sent. "
        "Subsequent emails from the OEM are 'oem_message'. Internal notes are "
        "'note'. Parts shipments are 'parts'. Site visits are 'field_visit'. "
        "Status changes (e.g., when claim was resolved) are 'status_change' "
        "with from_status and to_status set.\n"
        "- Extract occurred_at timestamps from email dates / form dates in "
        "ISO 8601 format. Omit (null) when unknown.\n"
        "- claim_date is the date the claim was originally filed with the "
        "OEM (or, if not on the form, the date the failure occurred). "
        "Format YYYY-MM-DD. Used downstream to look up site events around "
        "that time. Null if no date is usable.\n"
        "- Do not invent data not supported by the documents. Leave fields "
        "empty/null when unclear."
    )


@router.post(
    "/projects/{project_id}/historical-claim-extract",
    response_model=HistoricalClaimExtractResponse,
    dependencies=[Depends(dependencies.check_project_access_async)],
)
async def historical_claim_extract(
    project_id: UUID,
    context_json: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
    model: Annotated[str | None, Form()] = None,
):
    """Extract historical warranty claim fields from uploaded PDFs.

    Args:
        project_id: Project UUID from the path and access-control scope.
        context_json: JSON string for HistoricalClaimContext.
        files: PDFs to analyze (claim form + supporting docs).
        model: Optional OpenAI model override.
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail="At least one PDF file is required.",
        )
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_FILES} files allowed per request.",
        )
    try:
        context_obj = HistoricalClaimContext.model_validate_json(context_json)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid context_json: {e!s}",
        ) from e
    if context_obj.project_id is not None and context_obj.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="context_json project_id must match path project_id.",
        )
    context_obj.project_id = project_id

    client = build_openai_responses_client()
    uploaded_file_ids: list[str] = []
    try:
        for upload in files:
            content = await upload.read()
            if not content:
                raise HTTPException(
                    status_code=400,
                    detail=f"Empty file: {upload.filename}",
                )
            filename = upload.filename or "document.pdf"
            content_type = upload.content_type or "application/pdf"
            try:
                created = client.files.create(
                    file=(filename, content, content_type),
                    purpose="user_data",
                )
            except Exception as e:
                logger.exception("OpenAI file upload failed")
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenAI file upload failed: {e!s}",
                ) from e
            uploaded_file_ids.append(created.id)

        user_content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    "Call extract_historical_claim with structured data "
                    "based on the attached PDFs."
                ),
            },
        ]
        for file_id in uploaded_file_ids:
            user_content.append({"type": "input_file", "file_id": file_id})

        tools = [
            {
                "type": "function",
                "name": "extract_historical_claim",
                "description": ("Return structured historical warranty claim data."),
                "parameters": _extract_tool_schema(),
                "strict": True,
            }
        ]
        system_prompt_text = _system_prompt(context=context_obj)
        try:
            resp = client.responses.create(
                model=model or DEFAULT_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": system_prompt_text,
                            }
                        ],
                    },
                    {"role": "user", "content": user_content},
                ],
                tools=tools,
                tool_choice={
                    "type": "function",
                    "name": "extract_historical_claim",
                },
                temperature=0.2,
            )
        except Exception as e:
            logger.exception("OpenAI responses.create failed (historical claim)")
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI error: {e!s}",
            ) from e

        parsed = extract_response_tool_json(
            response=resp,
            tool_name="extract_historical_claim",
        )
        if not parsed:
            raise HTTPException(
                status_code=502,
                detail="Model did not return structured output.",
            )

        normalized = _normalize_response(parsed=parsed, context=context_obj)

        # Second turn: fetch candidate events per matched device, then ask
        # the LLM to pick a best event_id per device row.
        try:
            await _augment_with_event_suggestions(
                client=client,
                model=model or DEFAULT_MODEL,
                context=context_obj,
                response=normalized,
            )
        except Exception:
            logger.exception(
                "Historical claim extract - event suggestion turn failed; "
                "returning extraction without event suggestions.",
            )

        return normalized
    finally:
        for file_id in uploaded_file_ids:
            try:
                client.files.delete(file_id=file_id)
            except Exception:
                logger.warning(
                    "Failed to delete OpenAI file %s",
                    file_id,
                    exc_info=True,
                )


async def _fetch_candidate_events(
    *,
    project_name_short: str,
    device_ids: list[int],
    cutoff: datetime.datetime,
) -> list[CandidateEvent]:
    """Fetch closed/open events for given devices that started on/before cutoff.

    Args:
        project_name_short: Project schema name.
        device_ids: Device ids to look up events for.
        cutoff: Only return events whose time_start <= cutoff.

    Returns:
        List of candidate events.
    """
    if not device_ids:
        return []
    events_query = core_events.get_events_with_device_info(
        device_ids=device_ids,
        open=False,
        end=cutoff,
    )
    events_df = await events_query.get_async(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if events_df is None or events_df.is_empty():
        return []
    rows = events_df.to_dicts()

    failure_mode_ids = sorted(
        {
            int(r["failure_mode_id"])
            for r in rows
            if r.get("failure_mode_id") is not None
        }
    )
    fm_name_by_id: dict[int, str] = {}
    if failure_mode_ids:
        fm_rows = await get_failure_modes(
            failure_mode_ids=failure_mode_ids,
        ).get_async(output_type=OutputType.SQLALCHEMY)
        for fm in fm_rows or []:
            fm_name_by_id[int(fm.failure_mode_id)] = fm.name_long or fm.name_short or ""

    candidates: list[CandidateEvent] = []
    for r in rows:
        try:
            candidates.append(
                CandidateEvent(
                    event_id=int(r["event_id"]),
                    device_id=int(r["device_id"]),
                    time_start=r["time_start"],
                    time_end=r.get("time_end"),
                    failure_mode=fm_name_by_id.get(
                        int(r["failure_mode_id"])
                        if r.get("failure_mode_id") is not None
                        else -1
                    ),
                )
            )
        except Exception:
            continue
    candidates.sort(key=lambda c: c.time_start, reverse=True)
    return candidates


async def _augment_with_event_suggestions(
    *,
    client: Any,
    model: str,
    context: HistoricalClaimContext,
    response: HistoricalClaimExtractResponse,
) -> None:
    """Run second LLM turn to attach candidate events + suggested event_id.

    Mutates ``response`` in place by populating
    ``response.device_event_candidates`` and ``ExtractedDevice.event_id``.

    Args:
        client: OpenAI client.
        model: Model name.
        context: Original request context (project_id used for DB lookup).
        response: First-turn normalized response.
    """
    if context.project_id is None:
        logger.info(
            "Historical claim extract - second turn skipped: no project_id in context.",
        )
        return

    matched_device_ids = sorted(
        {d.device_id for d in response.devices if d.device_id is not None}
    )
    if not matched_device_ids:
        logger.info(
            "Historical claim extract - second turn skipped: no matched "
            "device_ids in extraction.",
        )
        return

    cutoff = _resolve_event_cutoff(response=response)
    logger.info(
        "Historical claim extract - second turn: project_id=%s, "
        "matched_device_ids=%s, cutoff=%s, claim_date=%s",
        context.project_id,
        matched_device_ids,
        cutoff.isoformat(),
        response.claim_date.isoformat() if response.claim_date else None,
    )

    project_name_short = await get_project_name_short_async(
        project_id=context.project_id,
    )
    if not project_name_short:
        logger.warning(
            "Historical claim extract - second turn skipped: could not "
            "resolve project_name_short for project_id=%s.",
            context.project_id,
        )
        return

    candidates = await _fetch_candidate_events(
        project_name_short=project_name_short,
        device_ids=matched_device_ids,
        cutoff=cutoff,
    )
    logger.info(
        "Historical claim extract - second turn: fetched %d candidate "
        "events across %d device(s) from schema=%s",
        len(candidates),
        len(matched_device_ids),
        project_name_short,
    )
    if not candidates:
        return

    candidates_by_device: dict[int, list[CandidateEvent]] = {}
    for c in candidates:
        candidates_by_device.setdefault(c.device_id, []).append(c)

    candidates_by_row: dict[int, list[CandidateEvent]] = {}
    rows_for_prompt: list[dict[str, Any]] = []
    for idx, dev in enumerate(response.devices):
        if dev.device_id is None:
            continue
        per_device = candidates_by_device.get(dev.device_id, [])
        if not per_device:
            continue
        candidates_by_row[idx] = per_device
        rows_for_prompt.append(
            {
                "row_index": idx,
                "device_id": dev.device_id,
                "device_name_hint": dev.device_name_hint,
                "notes": dev.notes,
                "candidates": [
                    {
                        "event_id": c.event_id,
                        "time_start": c.time_start.isoformat(),
                        "time_end": (c.time_end.isoformat() if c.time_end else None),
                        "failure_mode": c.failure_mode,
                    }
                    for c in per_device[:25]
                ],
            }
        )

    response.device_event_candidates = candidates_by_row

    if not rows_for_prompt:
        logger.info(
            "Historical claim extract - second turn skipped: no device rows "
            "have any candidate events.",
        )
        return

    system_text = (
        "You are linking historical warranty claim devices to detected "
        "site events. For each device row, pick the single best matching "
        "event_id from its candidates list, or null if no candidate is a "
        "credible match. Prefer events whose failure_mode aligns with the "
        "device row's notes/symptoms and whose time_start is closest to "
        "(but not after) the claim date "
        f"({response.claim_date.isoformat() if response.claim_date else 'unknown'}). "
        "Only return event_ids that appear in the candidates list for that "
        "row. Do not invent events."
    )
    user_text = (
        "Claim summary: "
        f"{response.summary or '(none)'}\n\n"
        "Device rows + candidate events:\n"
        f"{json.dumps(rows_for_prompt, ensure_ascii=False)}"
    )

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_text}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                },
            ],
            tools=[
                {
                    "type": "function",
                    "name": "suggest_claim_events",
                    "description": (
                        "Return a chosen event_id (or null) for each device row index."
                    ),
                    "parameters": _suggest_events_tool_schema(),
                    "strict": True,
                }
            ],
            tool_choice={
                "type": "function",
                "name": "suggest_claim_events",
            },
            temperature=0.1,
        )
    except Exception:
        logger.exception("OpenAI second-turn (suggest_claim_events) failed")
        return

    parsed = extract_response_tool_json(
        response=resp,
        tool_name="suggest_claim_events",
    )
    if not parsed:
        logger.warning(
            "Historical claim extract - second turn returned no parseable tool output.",
        )
        return

    logger.info(
        "Historical claim extract - second turn raw output:\n%s",
        json.dumps(parsed, ensure_ascii=False, indent=2),
    )

    applied: list[tuple[int, int]] = []
    for entry in parsed.get("device_events") or []:
        try:
            row_idx = int(entry.get("row_index"))
        except Exception:
            continue
        if row_idx < 0 or row_idx >= len(response.devices):
            continue
        suggested = entry.get("event_id")
        if not isinstance(suggested, int):
            continue
        valid_ids = {c.event_id for c in candidates_by_row.get(row_idx, [])}
        if suggested in valid_ids:
            response.devices[row_idx].event_id = suggested
            applied.append((row_idx, suggested))

    logger.info(
        "Historical claim extract - second turn applied %d event suggestion(s): %s",
        len(applied),
        applied,
    )


def _resolve_event_cutoff(
    *,
    response: HistoricalClaimExtractResponse,
) -> datetime.datetime:
    """Return the datetime cutoff used to filter candidate events.

    Args:
        response: Normalized first-turn response.

    Returns:
        Datetime threshold; events with time_start <= cutoff are eligible.
    """
    if response.claim_date is not None:
        return datetime.datetime.combine(
            response.claim_date,
            datetime.time(23, 59, 59),
            tzinfo=datetime.UTC,
        )
    occurred = [u.occurred_at for u in response.updates if u.occurred_at is not None]
    if occurred:
        return max(occurred)
    return datetime.datetime.now(datetime.UTC)


def _normalize_response(  # noqa: C901
    *,
    parsed: dict[str, Any],
    context: HistoricalClaimContext,
) -> HistoricalClaimExtractResponse:
    """Coerce model output into the typed response, filtering invalid values.

    Args:
        parsed: Raw dict from the model's function call.
        context: Request context (used to validate claim_config_id/device_id).

    Returns:
        Cleaned response payload.
    """
    valid_config_ids = {c.claim_config_id for c in context.claim_configs}
    valid_device_ids = {d.device_id for d in context.devices}
    device_type_by_device_id = {
        d.device_id: d.device_type_id
        for d in context.devices
        if d.device_type_id is not None
    }
    valid_device_type_ids = {dt.device_type_id for dt in context.device_types}
    valid_device_type_ids.update(device_type_by_device_id.values())

    raw_config_id = parsed.get("claim_config_id")
    claim_config_id: int | None = None
    if isinstance(raw_config_id, int) and raw_config_id in valid_config_ids:
        claim_config_id = raw_config_id

    raw_status = str(parsed.get("status") or "").strip().lower()
    status = raw_status if raw_status in CLAIM_STATUS_VALUES else "closed"

    devices: list[ExtractedDevice] = []
    for row in parsed.get("devices") or []:
        try:
            did = row.get("device_id")
            if not isinstance(did, int) or did not in valid_device_ids:
                did = None
            dtid = row.get("device_type_id")
            if not isinstance(dtid, int) or dtid not in valid_device_type_ids:
                dtid = None
            if did is not None:
                dtid = device_type_by_device_id.get(did, dtid)
            devices.append(
                ExtractedDevice(
                    device_id=did,
                    device_type_id=dtid,
                    device_name_hint=str(row.get("device_name_hint") or ""),
                    oem_serial_number=str(row.get("oem_serial_number") or ""),
                    oem_part_number=str(row.get("oem_part_number") or ""),
                    notes=str(row.get("notes") or ""),
                )
            )
        except Exception:
            continue

    updates: list[ExtractedUpdate] = []
    for row in parsed.get("updates") or []:
        try:
            update_type = str(row.get("update_type") or "").strip().lower()
            if update_type not in CLAIM_UPDATE_TYPE_VALUES:
                continue
            occurred_at_raw = row.get("occurred_at")
            occurred_at: datetime.datetime | None = None
            if isinstance(occurred_at_raw, str) and occurred_at_raw.strip():
                try:
                    occurred_at = datetime.datetime.fromisoformat(
                        occurred_at_raw.replace("Z", "+00:00"),
                    )
                except ValueError:
                    occurred_at = None
            from_status_raw = row.get("from_status")
            from_status = (
                from_status_raw
                if isinstance(from_status_raw, str)
                and from_status_raw in CLAIM_STATUS_VALUES
                else None
            )
            to_status_raw = row.get("to_status")
            to_status = (
                to_status_raw
                if isinstance(to_status_raw, str)
                and to_status_raw in CLAIM_STATUS_VALUES
                else None
            )
            updates.append(
                ExtractedUpdate(
                    update_type=update_type,
                    message=str(row.get("message") or ""),
                    occurred_at=occurred_at,
                    from_status=from_status,
                    to_status=to_status,
                )
            )
        except Exception:
            continue

    raw_claim_date = parsed.get("claim_date")
    claim_date: datetime.date | None = None
    if isinstance(raw_claim_date, str) and raw_claim_date.strip():
        try:
            claim_date = datetime.date.fromisoformat(raw_claim_date.strip()[:10])
        except Exception:
            claim_date = None

    return HistoricalClaimExtractResponse(
        claim_config_id=claim_config_id,
        oem_name_suggested=(
            None
            if claim_config_id is not None
            else (
                str(parsed.get("oem_name_suggested")).strip()
                if parsed.get("oem_name_suggested")
                else None
            )
        ),
        summary=str(parsed.get("summary") or "").strip(),
        external_reference=(
            str(parsed["external_reference"]).strip()
            if parsed.get("external_reference")
            else None
        ),
        status=status,
        claim_date=claim_date,
        devices=devices,
        updates=updates,
    )
