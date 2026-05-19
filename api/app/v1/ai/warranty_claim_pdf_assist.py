"""AI-assisted mapping of warranty claim data to PDF AcroForm fields or overlays."""

import base64
import json
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.logger import get_logger
from app.v1.ai._openai_helpers import (
    build_openai_responses_client,
    extract_response_tool_json,
)

logger = get_logger(name=__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_VISION_PAGES = 5
DEFAULT_MODEL_ACRO = "gpt-5-mini"
DEFAULT_MODEL_VISION = "gpt-5-mini"
ACRO_FIELD_PROMPT_EXCLUDE = {
    "existing_value",
    "height",
    "rect",
    "width",
    "x",
    "y",
}
PREVIOUS_CLAIM_REUSABLE_TERMS = {
    "address",
    "company",
    "customer",
    "gate",
    "model",
    "phone",
    "poc",
    "requirement",
    "site",
}
PREVIOUS_CLAIM_EXCLUDED_TERMS = {
    "date",
    "description",
    "event",
    "failure",
    "fault",
    "issue",
    "part",
    "problem",
    "serial",
    "ticket",
}


class ClaimDevicePayload(BaseModel):
    """One device row from the claim wizard."""

    device_name: str = ""
    device_brand: str = ""
    device_model: str = ""
    oem_serial_number: str = ""
    oem_part_number: str = ""
    notes: str = ""
    event_id: int | None = None


class ClaimEventPayload(BaseModel):
    """One event related to the claim."""

    event_id: int | None = None
    device_id: int | None = None
    time_start: str = ""
    time_end: str = ""
    failure_mode: str = ""
    root_cause: str = ""


class ClaimContextPayload(BaseModel):
    """Structured claim context for the model."""

    project: dict[str, Any] = Field(default_factory=dict)
    project_name: str = ""
    company_name: str = ""
    user_first_name: str = ""
    user_last_name: str = ""
    user_email: str = ""
    claim_id_display: str = ""
    phone: str = ""
    summary: str = ""
    external_reference: str = ""
    oem_name: str = ""
    today_date_display: str = ""
    declaration_date_display: str = ""
    first_issue_date_display: str = ""
    previous_claim_example: dict[str, Any] = Field(default_factory=dict)
    events: list[ClaimEventPayload] = Field(default_factory=list)
    devices: list[ClaimDevicePayload] = Field(default_factory=list)


class VisionPagePayload(BaseModel):
    """One rasterized PDF page for vision placement."""

    page_number: int = Field(ge=1)
    image_base64: str
    media_type: str = "image/png"


class AcroFieldPayload(BaseModel):
    """One AcroForm widget/input detected in the PDF."""

    field_name: str
    field_type: str = ""
    page: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    rect: list[float] = Field(default_factory=list)
    existing_value: str = ""
    nearby_label: str | None = None
    nearby_label_source: Literal["left", "above"] | None = None


class WarrantyClaimPdfAssistRequest(BaseModel):
    """Request for AcroForm fill mapping or vision overlay suggestions."""

    mode: Literal["acro", "vision"]
    claim_context: ClaimContextPayload
    model: str | None = None
    acro_fields: list[AcroFieldPayload] | None = None
    pages: list[VisionPagePayload] | None = None


class PdfAnnotationSuggestion(BaseModel):
    """One text overlay in PDF display coordinates (width 612pt, top-left origin)."""

    page: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    text: str
    font_size: float = Field(default=11, ge=6, le=24)


class WarrantyClaimPdfAssistResponse(BaseModel):
    """Mapped Acro values and/or overlay annotations."""

    acro_values: dict[str, str] | None = None
    annotations: list[PdfAnnotationSuggestion] | None = None


IGNORED_MODEL_TEXT_VALUES = {
    "",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "not provided",
}


def _join_non_empty(*parts: str) -> str:
    """Join non-empty strings with single spaces.

    Args:
        *parts: Candidate strings to join.

    Returns:
        Normalized combined string.
    """
    return " ".join(part.strip() for part in parts if part.strip())


def _acro_requested_text(*, acro_fields: list[AcroFieldPayload]) -> str:
    """Return searchable text for fields present in the current PDF.

    Args:
        acro_fields: PDF AcroForm fields and nearby labels.

    Returns:
        Lowercase field and label text.
    """
    parts: list[str] = []
    for field in acro_fields:
        parts.append(field.field_name)
        if field.nearby_label:
            parts.append(field.nearby_label)
        if field.nearby_label_source:
            parts.append(field.nearby_label_source)
    return " ".join(parts).lower()[:4000]


def _field_text_requests_any(*, requested_text: str, terms: set[str]) -> bool:
    """Return whether PDF fields appear to request one of the terms.

    Args:
        requested_text: Lowercase AcroForm field and label text.
        terms: Search terms to test.

    Returns:
        True when any term is present.
    """
    return any(term in requested_text for term in terms)


def _compact_filled_fields_text(*, text: Any, max_chars: int = 700) -> str:
    """Keep only stable reusable prior AcroForm field/value text.

    Args:
        text: Previous filled PDF text candidate.
        max_chars: Maximum output length.

    Returns:
        Newline-delimited field/value lines.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        match = re.match(r"^([^:=]{1,120})\s*[:=]\s*(.{1,300})$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if not key or _is_ignored_model_text(value=value):
            continue
        normalized_key = _normalize_model_text(value=key)
        if not any(term in normalized_key for term in PREVIOUS_CLAIM_REUSABLE_TERMS):
            continue
        if any(term in normalized_key for term in PREVIOUS_CLAIM_EXCLUDED_TERMS):
            continue
        lines.append(f"{key}: {value}")
        if sum(len(item) + 1 for item in lines) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]


def _previous_claim_prompt_payload(
    *,
    previous_claim_example: dict[str, Any],
) -> dict[str, str]:
    """Build compact prior claim context.

    Args:
        previous_claim_example: Raw previous claim example payload.

    Returns:
        Previous claim example limited to filled AcroForm field/value text.
    """
    filled_fields = _compact_filled_fields_text(
        text=(
            previous_claim_example.get("filled_fields")
            or previous_claim_example.get("filled_pdf_text")
        ),
    )
    return {"filled_fields": filled_fields} if filled_fields else {}


def _project_prompt_metadata(
    *,
    project_row: dict[str, Any],
    requested_text: str,
) -> dict[str, Any]:
    """Build project metadata only when the PDF appears to request it.

    Args:
        project_row: Raw project payload.
        requested_text: Lowercase AcroForm field and label text.

    Returns:
        Minimal project metadata for requested fields.
    """
    metadata: dict[str, Any] = {}
    if not project_row:
        return metadata

    if _field_text_requests_any(
        requested_text=requested_text,
        terms={"address", "location"},
    ):
        site_address = project_row.get("address")
        if isinstance(site_address, str) and site_address.strip():
            metadata["site_address"] = site_address.strip()

    if _field_text_requests_any(
        requested_text=requested_text,
        terms={"altitude", "elevation"},
    ):
        site_altitude = project_row.get("elevation")
        if site_altitude is not None:
            metadata["site_altitude"] = site_altitude
            metadata["site_elevation"] = site_altitude

    return metadata


def _normalize_model_text(*, value: str) -> str:
    """Normalize model text for filtering and dedupe.

    Args:
        value: Raw text from model output.

    Returns:
        Lowercased, whitespace-normalized string.
    """
    return re.sub(r"\s+", " ", value).strip().lower()


def _is_ignored_model_text(*, value: str) -> bool:
    """Return whether a model value should be ignored.

    Args:
        value: Raw model text.

    Returns:
        True when the value is empty or placeholder-like.
    """
    return _normalize_model_text(value=value) in IGNORED_MODEL_TEXT_VALUES


def _claim_context_prompt_payload(
    *,
    claim_context: ClaimContextPayload,
    requested_text: str = "",
) -> dict[str, Any]:
    """Build compact prompt context with derived helper fields.

    Args:
        claim_context: Request payload from the claim wizard.
        requested_text: Lowercase text describing requested PDF fields.

    Returns:
        Dict sent to the model.
    """
    ctx_json: dict[str, Any] = {}

    def add_text(*, key: str, value: str) -> None:
        """Add non-empty prompt text.

        Args:
            key: Prompt payload key.
            value: Candidate value.
        """
        if value.strip():
            ctx_json[key] = value.strip()

    wants_site = _field_text_requests_any(
        requested_text=requested_text,
        terms={"site", "project", "plant", "address", "location"},
    )
    wants_company = _field_text_requests_any(
        requested_text=requested_text,
        terms={"company", "customer", "owner", "operator", "end-user"},
    )
    wants_contact = _field_text_requests_any(
        requested_text=requested_text,
        terms={
            "claimant",
            "contact",
            "declarant",
            "email",
            "name",
            "phone",
            "poc",
            "signature",
        },
    )
    wants_date = _field_text_requests_any(
        requested_text=requested_text,
        terms={"date", "failure", "issue", "signature"},
    )
    wants_issue_detail = _field_text_requests_any(
        requested_text=requested_text,
        terms={"issue", "problem", "failure", "description", "fault", "alarm"},
    )
    wants_device = _field_text_requests_any(
        requested_text=requested_text,
        terms={"device", "model", "part", "product", "serial", "sn"},
    )
    if wants_site:
        add_text(key="project_name", value=claim_context.project_name)
    if wants_company:
        add_text(key="company_name", value=claim_context.company_name)
    if wants_contact:
        add_text(key="user_email", value=claim_context.user_email)
        add_text(key="phone", value=claim_context.phone)
    if wants_date:
        add_text(
            key="today_date_display",
            value=claim_context.today_date_display,
        )
        add_text(
            key="declaration_date_display",
            value=claim_context.declaration_date_display,
        )
        add_text(
            key="first_issue_date_display",
            value=claim_context.first_issue_date_display,
        )
    if wants_issue_detail:
        add_text(key="summary", value=claim_context.summary)
    if _field_text_requests_any(
        requested_text=requested_text,
        terms={"manufacturer", "oem"},
    ):
        add_text(key="oem_name", value=claim_context.oem_name)
    project_row = claim_context.project
    ctx_json.update(
        _project_prompt_metadata(
            project_row=project_row,
            requested_text=requested_text,
        ),
    )

    full_name = _join_non_empty(
        claim_context.user_first_name,
        claim_context.user_last_name,
    )
    if full_name and wants_contact:
        ctx_json["user_full_name"] = full_name

    if _field_text_requests_any(
        requested_text=requested_text,
        terms={"claim", "case", "ticket", "rma", "reference"},
    ):
        reference_candidates = [
            value.strip()
            for value in [
                claim_context.claim_id_display,
                claim_context.external_reference,
            ]
            if value.strip()
        ]
        if reference_candidates:
            ctx_json["reference_candidates"] = reference_candidates

    previous_claim_example = _previous_claim_prompt_payload(
        previous_claim_example=claim_context.previous_claim_example,
    )
    if previous_claim_example:
        ctx_json["previous_claim_example"] = previous_claim_example

    event_start_dates = [
        event.time_start.strip()
        for event in claim_context.events
        if event.time_start.strip()
    ]
    if wants_date and event_start_dates and "first_issue_date_display" not in ctx_json:
        ctx_json["first_issue_date_display"] = min(event_start_dates)[:10]

    if wants_issue_detail or wants_date:
        events: list[dict[str, Any]] = []
        for event in claim_context.events:
            item: dict[str, Any] = {}
            if event.event_id is not None:
                item["event"] = event.event_id
            if event.device_id is not None:
                item["device_id"] = event.device_id
            if event.failure_mode.strip():
                item["failure"] = event.failure_mode.strip()
            if event.root_cause.strip():
                item["root_cause"] = event.root_cause.strip()
            if item:
                events.append(item)
        if events:
            ctx_json["events"] = events

    if wants_device or wants_issue_detail:
        devices: list[dict[str, Any]] = []
        for device in claim_context.devices:
            device_item: dict[str, Any] = {}
            device_name = device.device_name.strip()
            model = _join_non_empty(device.device_brand, device.device_model)
            if device.event_id is not None:
                device_item["event"] = device.event_id
            if device_name:
                device_item["device"] = device_name
            if model:
                device_item["model"] = model
            if device.oem_serial_number.strip():
                device_item["serial"] = device.oem_serial_number.strip()
            if device.oem_part_number.strip():
                device_item["part"] = device.oem_part_number.strip()
            if device.notes.strip():
                device_item["notes"] = device.notes.strip()
            if device_item:
                devices.append(device_item)
        if devices:
            ctx_json["devices"] = devices
    return ctx_json


def _dedupe_annotations(
    *,
    annotations: list[PdfAnnotationSuggestion],
) -> list[PdfAnnotationSuggestion]:
    """Drop near-duplicate annotation suggestions.

    Args:
        annotations: Parsed model suggestions.

    Returns:
        Filtered annotations in original order.
    """
    filtered: list[PdfAnnotationSuggestion] = []
    for annotation in annotations:
        normalized_text = _normalize_model_text(value=annotation.text)
        is_duplicate = any(
            existing.page == annotation.page
            and _normalize_model_text(value=existing.text) == normalized_text
            and abs(existing.x - annotation.x) <= 24
            and abs(existing.y - annotation.y) <= 16
            for existing in filtered
        )
        if is_duplicate:
            continue
        filtered.append(annotation)
    return filtered


def _should_send_acro_field_to_model(*, field: AcroFieldPayload) -> bool:
    """Return whether a field needs model-filled output.

    Args:
        field: PDF AcroForm field metadata.

    Returns:
        True when the field has a name and no existing meaningful value.
    """
    return bool(field.field_name.strip()) and _is_ignored_model_text(
        value=field.existing_value,
    )


@router.post(
    "/warranty-claim-pdf-assist",
    response_model=WarrantyClaimPdfAssistResponse,
)
async def warranty_claim_pdf_assist(
    *,
    request: WarrantyClaimPdfAssistRequest,
):
    """Map claim context to PDF AcroForm field values or suggest overlay positions.

    Args:
        request: Mode, context, and either AcroForm fields or page images.
    """
    if request.mode == "acro":
        acro_fields = request.acro_fields or []
        if not acro_fields:
            raise HTTPException(
                status_code=400,
                detail="acro_fields is required for mode=acro",
            )
        return await _assist_acro(
            claim_context=request.claim_context,
            acro_fields=acro_fields,
            model=request.model or DEFAULT_MODEL_ACRO,
        )

    pages = request.pages or []
    if not pages:
        raise HTTPException(
            status_code=400,
            detail="pages is required for mode=vision",
        )
    if len(pages) > MAX_VISION_PAGES:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_VISION_PAGES} pages allowed",
        )
    return await _assist_vision(
        claim_context=request.claim_context,
        pages=pages,
        model=request.model or DEFAULT_MODEL_VISION,
    )


async def _assist_acro(
    *,
    claim_context: ClaimContextPayload,
    acro_fields: list[AcroFieldPayload],
    model: str,
) -> WarrantyClaimPdfAssistResponse:
    """Fill AcroForm fields from claim context using the chat model.

    Args:
        claim_context: Wizard and user context.
        acro_fields: Exact PDF field metadata to fill.
        model: OpenAI model id.

    Returns:
        Response with acro_values only.
    """
    fields_to_fill = [
        field for field in acro_fields if _should_send_acro_field_to_model(field=field)
    ]
    if not fields_to_fill:
        return WarrantyClaimPdfAssistResponse(acro_values={})

    client = build_openai_responses_client()
    field_payloads = [
        field.model_dump(
            exclude=ACRO_FIELD_PROMPT_EXCLUDE,
            exclude_none=True,
        )
        for field in fields_to_fill
    ]
    ctx_json = _claim_context_prompt_payload(
        claim_context=claim_context,
        requested_text=_acro_requested_text(acro_fields=fields_to_fill),
    )
    acro_field_names = [field["field_name"] for field in field_payloads]
    system_prompt = (
        "Fill only blank AcroForm fields. Rules: "
        "- Use exact field_name values from acro_fields. "
        "- Disambiguate with nearby_label; left labels beat above labels. "
        "- customer/company/site -> company_name/project_name/site_address. "
        "- claimant/contact/declarant/signature -> user_full_name; "
        "email -> user_email; phone -> phone or reusable prior phone. "
        "- claim/case/ticket/RMA/reference -> reference_candidates. "
        "- today's/current/form completion date -> today_date_display; "
        "- first issue/failure date -> first_issue_date_display; "
        "signature date -> declaration_date_display. "
        "- product/model/part/serial/fault/description -> devices/events/summary. "
        "- Previous claim values are only stable contact/site carryover. "
        "- Omit unsupported fields; never invent facts."
    )
    user_text = json.dumps(
        {
            "claim_context": ctx_json,
            "acro_fields": field_payloads,
            "instruction": (
                "Call fill_acro_fields with entries: each field_name must be "
                "exactly one of the acro_fields field_name values."
            ),
        },
        ensure_ascii=False,
    )
    openai_input: Any = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_text}],
        },
    ]
    tools: Any = [
        {
            "type": "function",
            "name": "fill_acro_fields",
            "description": (
                "Return PDF AcroForm text field values as name/value pairs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "description": "One entry per field to fill",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field_name": {
                                    "type": "string",
                                    "description": "Exact Acro field name",
                                },
                                "value": {"type": "string"},
                            },
                            "required": ["field_name", "value"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["entries"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]
    try:
        resp = client.responses.create(
            model=model,
            tools=tools,
            input=openai_input,
        )
    except Exception as e:
        logger.exception("OpenAI responses.create failed (acro)")
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI error: {e!s}",
        ) from e

    parsed = extract_response_tool_json(
        response=resp,
        tool_name="fill_acro_fields",
    )
    raw_values: dict[str, str] = {}
    if parsed and isinstance(parsed.get("entries"), list):
        for row in parsed["entries"]:
            try:
                fn = str(row.get("field_name", "")).strip()
                raw_values[fn] = str(row.get("value", "")).strip()
            except Exception:
                continue

    allowed = set(acro_field_names)
    acro_values = {
        key: value
        for key, value in raw_values.items()
        if key in allowed and value and not _is_ignored_model_text(value=value)
    }
    return WarrantyClaimPdfAssistResponse(acro_values=acro_values)


async def _assist_vision(
    *,
    claim_context: ClaimContextPayload,
    pages: list[VisionPagePayload],
    model: str,
) -> WarrantyClaimPdfAssistResponse:
    """Suggest overlay annotations from page images and claim context.

    Args:
        claim_context: Wizard and user context.
        pages: Base64 PNG/JPEG images per page.
        model: Vision-capable OpenAI model id.

    Returns:
        Response with annotations only.
    """
    client = build_openai_responses_client()
    ctx_json = _claim_context_prompt_payload(
        claim_context=claim_context,
        requested_text=(
            "site project plant address location company customer owner "
            "operator claimant contact declarant email name phone poc "
            "signature date failure issue description problem fault alarm "
            "claim case ticket rma reference manufacturer oem device model "
            "part product serial sn"
        ),
    )
    coord_help = (
        "Coordinate system: origin at top-left of each page image. "
        "Units match a PDF render width of 612 points (standard US Letter "
        "width). x increases to the right, y increases downward. "
        "Place each text block so it sits on or just below the blank line "
        "or box for that label. Use font_size 10-12 for normal text, 9 for "
        "dense areas."
    )
    system_prompt = (
        "You help fill OEM warranty claim PDFs. "
        f"{coord_help} "
        "Return annotations only when you can see a clear field, line, box, "
        "or table cell that matches the data. "
        "Prioritize customer/company, contact name, email, claim/reference "
        "number, project/site, today's date, declaration date, "
        "product/model/part/serial, issue description, and signature name. "
        "Use claim_context.user_full_name for claimant/declarant/signature "
        "name fields. Use claim_context.company_name for customer/company "
        "fields. Use claim_context.reference_candidates for claim or case "
        "number fields. Use claim_context.today_date_display for today's, "
        "current, or form completion date fields. "
        "For device tables, place product/model/serial/part values inside the "
        "matching visible row or the first available row, using device "
        "brand/model when those are available. "
        "Avoid placing text on instructional paragraphs, section headers, or "
        "labels themselves. "
        "Do not repeat the same value multiple times on the same page unless "
        "the form clearly repeats that field in separate places. "
        "Use only information from claim_context; do not invent site dates "
        "or events. If a value is unknown, skip that annotation or use empty "
        "string sparingly. "
        f"Page numbers must match the images (1..{len(pages)})."
    )
    user_parts: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": json.dumps(
                {
                    "claim_context": ctx_json,
                    "pages_sent": [p.page_number for p in pages],
                    "instruction": (
                        "Call suggest_pdf_annotations with annotations array. "
                        "Each item: page (int), x, y, text, font_size optional."
                    ),
                },
                ensure_ascii=False,
            ),
        }
    ]
    for p in pages:
        try:
            raw_b64 = p.image_base64.strip()
            if "," in raw_b64 and raw_b64.startswith("data:"):
                raw_b64 = raw_b64.split(",", 1)[1]
            decoded = base64.b64decode(raw_b64, validate=True)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 for page {p.page_number}: {e!s}",
            ) from e
        if len(raw_b64) < 32 or len(decoded) < 8:
            raise HTTPException(
                status_code=400,
                detail=(f"Empty or too-small image payload for page {p.page_number}"),
            )
        mime = p.media_type if "/" in p.media_type else "image/png"
        data_url = f"data:{mime};base64,{raw_b64}"
        user_parts.append(
            {
                "type": "input_text",
                "text": f"Page {p.page_number} image follows.",
            }
        )
        user_parts.append({"type": "input_image", "image_url": data_url})

    openai_input: Any = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}],
        },
        {"role": "user", "content": user_parts},
    ]
    tools: Any = [
        {
            "type": "function",
            "name": "suggest_pdf_annotations",
            "description": (
                "Suggested text overlays for warranty PDF in display coordinates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "annotations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "integer"},
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "text": {"type": "string"},
                                "font_size": {"type": "number"},
                            },
                            "required": ["page", "x", "y", "text", "font_size"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["annotations"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]
    try:
        resp = client.responses.create(
            model=model,
            tools=tools,
            input=openai_input,
        )
    except Exception as e:
        logger.exception("OpenAI responses.create failed (vision)")
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI error: {e!s}",
        ) from e

    parsed = extract_response_tool_json(
        response=resp,
        tool_name="suggest_pdf_annotations",
    )
    annotations: list[PdfAnnotationSuggestion] = []
    if parsed and isinstance(parsed.get("annotations"), list):
        page_nums = {p.page_number for p in pages}
        for item in parsed["annotations"]:
            try:
                page = int(item["page"])
                if page not in page_nums:
                    continue
                text = str(item.get("text", "")).strip()
                if not text or _is_ignored_model_text(value=text):
                    continue
                fs = item.get("font_size", 11)
                fs_f = float(fs) if fs is not None else 11.0
                annotations.append(
                    PdfAnnotationSuggestion(
                        page=page,
                        x=float(item["x"]),
                        y=float(item["y"]),
                        text=text,
                        font_size=max(6.0, min(24.0, fs_f)),
                    )
                )
            except Exception:
                continue

    return WarrantyClaimPdfAssistResponse(
        annotations=_dedupe_annotations(annotations=annotations),
    )
