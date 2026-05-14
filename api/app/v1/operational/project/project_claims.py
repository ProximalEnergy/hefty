"""API routes for warranty claims."""

import datetime
import logging
import re
from io import StringIO
from typing import Annotated, Any, cast
from uuid import UUID

import pandas as pd
import sqlalchemy as sa
from core.crud.operational import claim_configs as operational_claim_configs
from core.crud.project import claims as project_claims
from core.crud.project import tags as project_tags
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.domain.statuses import statuses as domain_statuses
from fastapi import (
    APIRouter,
    Body,
    Depends,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import dependencies, interfaces
from app._crud.operational import (
    claim_attachments,
)
from app._crud.operational import (
    claims as crud_claims,
)
from app._dependencies import authentication
from app._utils.claim_emails import (
    build_claim_submission_email_html,
    send_claim_submission_email,
)
from core import enumerations, models

router = APIRouter(
    prefix="/claims",
    tags=["project_claims"],
)

logger = logging.getLogger(__name__)

EVENT_DATA_WINDOW = datetime.timedelta(minutes=30)
EVENT_DATA_INTERVAL = enumerations.TimeInterval.ONE_MINUTE


def _resolve_claim_submit_to_emails(
    *,
    config: models.ClaimConfig | None,
    submit_opts: interfaces.ClaimSubmit,
) -> list[str]:
    """Resolve To recipients: explicit submit list or claim config default contact.

    Args:
        config: Claim configuration (OEM default contact).
        submit_opts: Submit payload with optional ``to_emails`` override.

    Returns:
        Non-empty list of recipient addresses, or empty when none apply.
    """
    to_out: list[str] = []
    raw = submit_opts.to_emails
    if raw is not None:
        to_out = [str(x).strip() for x in raw if x and str(x).strip()]
    if not to_out and config is not None and config.default_contact:
        one = str(config.default_contact).strip()
        if one:
            to_out = [one]
    return to_out


def _filename_part(*, value: object, fallback: str) -> str:
    """Build a readable filename segment from metadata.

    Args:
        value: Raw metadata value.
        fallback: Segment to use when the value is empty.
    """
    text = _present_string(value=value) or fallback
    text = re.sub(r"[^A-Za-z0-9._ -]+", "-", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = text.strip(".-_")
    return text or fallback


def _claim_event_data_filename(
    *,
    device_type: object,
    device_name_long: object,
    event_id: int,
) -> str:
    """Build a stable filename for an event data export.

    Args:
        device_type: Device type label for the event device.
        device_name_long: Long display name for the event device.
        event_id: Event included in the CSV export.
    """
    return (
        f"{_filename_part(value=device_type, fallback='device')}-"
        f"{_filename_part(value=device_name_long, fallback='unknown-device')}"
        f"_event-{event_id}.csv"
    )


def _present_string(*, value: object) -> str | None:
    """Return a non-empty string when a dataframe value is present.

    Args:
        value: Value from a pandas metadata row.
    """
    if value is None or pd.isna(cast(Any, value)):
        return None
    text = str(value).strip()
    return text or None


def _tag_column_label(*, row: pd.Series) -> str:
    """Create a readable, unique-ish CSV column label for a tag.

    Args:
        row: Tag metadata row from the project tags query.
    """
    tag_id = int(row["tag_id"])
    sensor_name = (
        _present_string(value=row.get("sensor_type_name_long"))
        or _present_string(value=row.get("sensor_type_name_short"))
        or f"Sensor {row.get('sensor_type_id')}"
    )
    tag_name = (
        _present_string(value=row.get("name_scada"))
        or _present_string(value=row.get("name_long"))
        or _present_string(value=row.get("name_short"))
        or f"tag_{tag_id}"
    )
    return f"{sensor_name} | {tag_name} | tag {tag_id}"


def _make_unique_columns(*, labels: dict[int, str]) -> dict[int, str]:
    """Ensure CSV column labels are unique.

    Args:
        labels: Mapping from tag id to desired CSV column label.
    """
    counts: dict[str, int] = {}
    out: dict[int, str] = {}
    for tag_id, label in labels.items():
        count = counts.get(label, 0)
        counts[label] = count + 1
        out[tag_id] = label if count == 0 else f"{label} ({count + 1})"
    return out


def _normalize_timeseries_dataframe(
    *,
    df: pd.DataFrame,
    project: models.Project,
) -> pd.DataFrame:
    """Index a timeseries dataframe by project-local timestamp.

    Args:
        df: Dataframe returned by ``DataTimeseries``.
        project: Project whose timezone should be used for CSV timestamps.
    """
    if df.empty:
        return df
    time_values: Any
    if df.index.name in {"time", "time_bucket"}:
        time_values = pd.to_datetime(df.index)
    elif "time" in df.columns:
        time_values = pd.to_datetime(df.pop("time"))
    elif "time_bucket" in df.columns:
        time_values = pd.to_datetime(df.pop("time_bucket"))
    else:
        return pd.DataFrame()
    if isinstance(time_values, pd.DatetimeIndex):
        if time_values.tz is None:
            time_values = time_values.tz_localize(project.time_zone)
        else:
            time_values = time_values.tz_convert(project.time_zone)
    elif time_values.dt.tz is None:
        time_values = time_values.dt.tz_localize(project.time_zone)
    else:
        time_values = time_values.dt.tz_convert(project.time_zone)
    df.index = time_values
    df.index.name = "time"
    df = df.set_axis([int(col) for col in df.columns], axis="columns")
    return df


def _build_status_label_frame(
    *,
    facts: list[dict],
    tag_ids: list[int],
    start: datetime.datetime,
    end: datetime.datetime,
    project: models.Project,
) -> pd.DataFrame:
    """Transform decoded status facts into one label column per status tag.

    Args:
        facts: Sparse decoded status rows from the status domain service.
        tag_ids: Status tag ids to include as columns.
        start: Export start timestamp.
        end: Export end timestamp.
        project: Project whose timezone should be used for the timeline.
    """
    timeline = pd.date_range(start, end, freq="1min")
    if timeline.tz is None:
        timeline = timeline.tz_localize(project.time_zone)
    else:
        timeline = timeline.tz_convert(project.time_zone)
    if not facts:
        return pd.DataFrame("Nominal", index=timeline, columns=tag_ids)

    facts_df = pd.DataFrame(facts)
    state_values = facts_df["resolved_state"].combine_first(facts_df["observed_bool"])
    facts_df["label"] = [
        f"{description}: {state}"
        for description, state in zip(
            facts_df["description"],
            state_values,
            strict=False,
        )
    ]
    cell_text = facts_df.groupby(["time", "tag_id"])["label"].agg(", ".join)
    wide = cell_text.unstack("tag_id").reindex(index=timeline, columns=tag_ids)
    return cast(pd.DataFrame, wide.fillna("Nominal"))


# ── Claim configs ──


@router.get(
    "/configs",
    response_model=list[interfaces.ClaimConfigResponse],
)
async def get_claim_configs_route(
    project_id: UUID,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_async_db),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """List claim configs for this project.

    Args:
        project_id: Project UUID.
        db: Async DB session.
        user: Authenticated user.
    """
    return await crud_claims.get_claim_configs(
        db,
        project_id=project_id,
        submitter_company_id=user.company_id,
    )


@router.post(
    "/configs",
    response_model=interfaces.ClaimConfigResponse,
)
async def create_claim_config_route(
    project_id: UUID,
    payload: interfaces.ClaimConfigCreate,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_async_db),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """Create a new claim config for this project.

    Args:
        project_id: Project UUID.
        payload: Claim config data.
        db: Async DB session.
        user: Authenticated user.
    """
    cc = await crud_claims.create_claim_config(
        db,
        submitter_company_id=user.company_id,
        counterparty_company_id=payload.counterparty_company_id,
        project_id=project_id,
        default_submission_channel=payload.default_submission_channel,
        default_contact=payload.default_contact,
        portal_url=payload.portal_url,
    )
    return interfaces.ClaimConfigResponse.model_validate(cc)


@router.patch(
    "/configs/{claim_config_id}",
    response_model=interfaces.ClaimConfigResponse,
)
async def patch_claim_config(
    project_id: UUID,
    claim_config_id: int,
    payload: interfaces.ClaimConfigUpdate,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_async_db),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """Update fields on a claim config.

    Args:
        project_id: Project UUID.
        claim_config_id: Config to update.
        payload: Fields to patch.
        db: Async DB session.
        user: Authenticated user.
    """
    claim_config_query = operational_claim_configs.query_claim_config(
        claim_config_id=claim_config_id,
    )
    existing = cast(
        models.ClaimConfig | None,
        await claim_config_query.get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        ),
    )
    if not existing or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Claim config not found")
    if existing.submitter_company_id != user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    fields_set = payload.model_fields_set
    cc = await crud_claims.update_claim_config(
        db,
        claim_config_id=claim_config_id,
        counterparty_company_id=payload.counterparty_company_id,
        default_submission_channel=payload.default_submission_channel,
        default_contact=payload.default_contact,
        portal_url=payload.portal_url,
        update_default_contact="default_contact" in fields_set,
        update_portal_url="portal_url" in fields_set,
    )
    if cc is None:
        raise HTTPException(status_code=404, detail="Claim config not found")
    counterparty_name = await db.scalar(
        sa.select(models.Company.name_long).where(
            models.Company.company_id == cc.counterparty_company_id
        )
    )
    return interfaces.ClaimConfigResponse(
        claim_config_id=cc.claim_config_id,
        submitter_company_id=cc.submitter_company_id,
        counterparty_company_id=cc.counterparty_company_id,
        project_id=cc.project_id,
        default_submission_channel=cc.default_submission_channel,
        default_contact=cc.default_contact,
        portal_url=cc.portal_url,
        counterparty_name=counterparty_name,
    )


@router.delete(
    "/configs/{claim_config_id}",
    status_code=204,
)
async def delete_claim_config_route(
    project_id: UUID,
    claim_config_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_async_db),
    ],
    project_db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """Delete a claim config. Refused if any claims reference it.

    Args:
        project_id: Project UUID.
        claim_config_id: Config to delete.
        db: Operational-schema async DB session (for the config).
        project_db: Project-scoped async DB session (for counting claims).
        user: Authenticated user.
    """
    claim_config_query = operational_claim_configs.query_claim_config(
        claim_config_id=claim_config_id,
    )
    existing = cast(
        models.ClaimConfig | None,
        await claim_config_query.get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        ),
    )
    if not existing or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="Claim config not found")
    if existing.submitter_company_id != user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    claim_count = await project_claims.query_count_claims_for_config(
        claim_config_id=claim_config_id,
    ).get_async(
        executor=project_db,
        output_type=OutputType.SQLALCHEMY,
    )
    n_claims = int(claim_count or 0)
    if n_claims > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete: {n_claims} claim(s) still reference this "
                "config. Delete or reassign those claims first."
            ),
        )

    deleted = await crud_claims.delete_claim_config(
        db,
        claim_config_id=claim_config_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Claim config not found")


# ── Claims CRUD ──


@router.get(
    "",
    response_model=list[interfaces.ClaimListItem],
)
async def get_project_claims_route(
    project_id: UUID,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """List all claims for a project.

    Args:
        project_id: Project UUID.
        db: Project-scoped async DB session.
    """
    return await crud_claims.get_project_claims(db, project_id=project_id)


@router.post(
    "",
    response_model=interfaces.ClaimListItem,
    status_code=201,
)
async def create_claim_route(
    payload: interfaces.ClaimCreate,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """Create a new draft claim.

    Args:
        payload: Claim creation data.
        db: Async DB session.
        user: Authenticated user.
    """
    claim = await crud_claims.create_claim(
        db,
        claim_config_id=payload.claim_config_id,
        user_id=user.user_id,
        summary=payload.summary,
        external_reference=payload.external_reference,
    )
    return interfaces.ClaimListItem(
        claim_id=claim.claim_id,
        claim_config_id=claim.claim_config_id,
        status=claim.status,
        summary=claim.summary,
        external_reference=claim.external_reference,
        device_count=0,
    )


@router.get("/event-data-csv", response_class=Response)
async def get_claim_event_data_csv(
    event_id: Annotated[int, Query()],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """Export the selected claim event's surrounding device data as CSV.

    Args:
        event_id: Event whose device data should be exported.
        project: Project scoped by the route path.
        project_db: Project-scoped database session.
    """
    event_metadata = project_db.execute(
        sa.select(
            models.Event,
            models.DeviceType.name_long,
            models.Device.name_long,
            models.Device.name_short,
        )
        .join(models.Device, models.Event.device_id == models.Device.device_id)
        .join(
            models.DeviceType,
            models.Device.device_type_id == models.DeviceType.device_type_id,
        )
        .where(models.Event.event_id == event_id)
    ).one_or_none()
    if event_metadata is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event, device_type, device_name_long, device_name_short = event_metadata

    start = event.time_start - EVENT_DATA_WINDOW
    end = event.time_start + EVENT_DATA_WINDOW
    tags_df = await project_tags.get_project_tags_v2(
        in_tsdb=True,
        device_ids=[event.device_id],
        deep=True,
    ).get_async(output_type=OutputType.POLARS, schema=project.name_short)
    if tags_df is None or tags_df.is_empty():
        raise HTTPException(
            status_code=404,
            detail="No timeseries tags configured for this event device",
        )

    data_timeseries = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_df,
        query_start=start,
        query_end=end,
        project_db=project_db,
        freq=EVENT_DATA_INTERVAL,
        ensure_full_range=True,
    ).get()
    data_df = _normalize_timeseries_dataframe(
        df=data_timeseries.df.to_pandas(),
        project=project,
    )
    if data_df.empty:
        empty_index = pd.date_range(start, end, freq="1min")
        if empty_index.tz is None:
            empty_index = empty_index.tz_localize(project.time_zone)
        else:
            empty_index = empty_index.tz_convert(project.time_zone)
        data_df = pd.DataFrame(index=empty_index)

    tags_pd = tags_df.to_pandas()
    tag_labels = _make_unique_columns(
        labels={
            int(row["tag_id"]): _tag_column_label(row=row)
            for _, row in tags_pd.iterrows()
        },
    )
    status_tag_ids = [
        int(row["tag_id"])
        for _, row in tags_pd[tags_pd["status_lookup_id"].notna()].iterrows()
    ]
    if status_tag_ids:
        decoded_status = await domain_statuses.get_status_timeseries_interpreted(
            project_db=project_db,
            project=project,
            tag_ids=status_tag_ids,
            start=start,
            end=end,
            get_all=True,
            freq=EVENT_DATA_INTERVAL,
        )
        status_df = _build_status_label_frame(
            facts=decoded_status,
            tag_ids=status_tag_ids,
            start=start,
            end=end,
            project=project,
        )
        for tag_id in status_tag_ids:
            data_df[tag_id] = status_df[tag_id].reindex(data_df.index).fillna("Nominal")

    ordered_cols = [int(row["tag_id"]) for _, row in tags_pd.iterrows()]
    available_cols = [col for col in ordered_cols if col in data_df.columns]
    out = data_df[available_cols].rename(columns=tag_labels)
    out = out.reset_index()
    out["time"] = pd.to_datetime(out["time"]).dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    csv_buffer = StringIO()
    out.to_csv(csv_buffer, index=False)
    filename = _claim_event_data_filename(
        device_type=device_type,
        device_name_long=device_name_long or device_name_short,
        event_id=event_id,
    )
    return Response(
        content=csv_buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{claim_id}",
    response_model=interfaces.ClaimDetailResponse,
)
async def get_claim_route(
    project_id: UUID,
    claim_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """Get full claim detail.

    Args:
        project_id: Project UUID.
        claim_id: Claim primary key.
        db: Project-scoped async DB session.
    """
    claim_query = project_claims.query_claim(
        claim_id=claim_id,
        project_id=project_id,
    )
    claim = cast(
        models.Claim | None,
        await claim_query.get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        ),
    )
    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found",
        )

    counterparty_name = None
    if claim.claim_config and claim.claim_config.counterparty_company:
        counterparty_name = claim.claim_config.counterparty_company.name_long

    updates = sorted(claim.updates, key=lambda u: u.created_at)
    created_at = updates[0].created_at if updates else None
    updated_at = updates[-1].created_at if updates else None

    attachments = await claim_attachments.get_claim_attachments(
        db=db,
        claim_id=claim_id,
    )

    devices_resp = []
    for cd in claim.devices:
        d_name = cd.device.name_short if cd.device else None
        devices_resp.append(
            interfaces.ClaimDeviceResponse(
                claim_device_id=cd.claim_device_id,
                claim_id=cd.claim_id,
                device_id=cd.device_id,
                event_id=cd.event_id,
                oem_serial_number=cd.oem_serial_number,
                oem_part_number=cd.oem_part_number,
                notes=cd.notes,
                device_name=d_name,
            )
        )

    updates_resp = []
    for u in updates:
        u_name = u.user.name_long if u.user else None
        updates_resp.append(
            interfaces.ClaimUpdateResponse(
                claim_update_id=u.claim_update_id,
                claim_id=u.claim_id,
                update_type=u.update_type,
                from_status=u.from_status,
                to_status=u.to_status,
                message=u.message,
                user_id=u.user_id,
                created_at=u.created_at,
                user_name=u_name,
            )
        )

    return interfaces.ClaimDetailResponse(
        claim_id=claim.claim_id,
        claim_config_id=claim.claim_config_id,
        status=claim.status,
        summary=claim.summary,
        external_reference=claim.external_reference,
        counterparty_name=counterparty_name,
        created_at=created_at,
        updated_at=updated_at,
        devices=devices_resp,
        updates=updates_resp,
        attachments=[interfaces.ClaimAttachmentInterface(**a) for a in attachments],
    )


@router.patch(
    "/{claim_id}",
    response_model=interfaces.ClaimListItem,
    dependencies=[Depends(authentication.get_user)],
)
async def patch_claim(
    claim_id: int,
    payload: interfaces.ClaimUpdateInterface,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """Update mutable claim fields.

    Args:
        claim_id: Claim primary key.
        payload: Fields to update.
        db: Async DB session.
    """
    claim = await crud_claims.update_claim(
        db,
        claim_id=claim_id,
        summary=payload.summary,
        external_reference=payload.external_reference,
        status=payload.status,
    )
    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found",
        )
    return interfaces.ClaimListItem(
        claim_id=claim.claim_id,
        claim_config_id=claim.claim_config_id,
        status=claim.status,
        summary=claim.summary,
        external_reference=claim.external_reference,
    )


@router.delete(
    "/{claim_id}",
    status_code=204,
)
async def delete_claim_route(
    project_id: UUID,
    claim_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """Delete a claim and all of its attachments.

    Drafts can be deleted by any user; non-draft claims can only be
    deleted by admins (or superadmins). Removing the claim also
    permanently deletes any attachment files from S3.

    Args:
        project_id: Project UUID.
        claim_id: Claim primary key.
        db: Project-scoped async DB session.
        user: Authenticated user.
    """
    claim_query = project_claims.query_claim(
        claim_id=claim_id,
        project_id=project_id,
    )
    claim = cast(
        models.Claim | None,
        await claim_query.get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        ),
    )
    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found",
        )
    if (
        claim.claim_config is None
        or claim.claim_config.submitter_company_id != user.company_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Cannot delete claims submitted by another company",
        )
    is_admin = user.user_type_id in (
        enumerations.UserTypeEnum.ADMIN,
        enumerations.UserTypeEnum.SUPERADMIN,
    )
    if claim.status != enumerations.ClaimStatus.DRAFT and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete non-draft claims",
        )

    attachments = await claim_attachments.get_claim_attachments(
        db=db,
        claim_id=claim_id,
    )
    for a in attachments:
        await claim_attachments.delete_claim_attachment(
            db=db,
            claim_id=claim_id,
            filename=a["filename"],
        )

    await crud_claims.delete_claim(db, claim_id=claim_id)


# ── Claim devices ──


@router.post(
    "/{claim_id}/devices",
    response_model=interfaces.ClaimDeviceResponse,
    status_code=201,
)
async def add_claim_device(
    claim_id: int,
    payload: interfaces.ClaimDeviceCreate,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """Add a device to a claim.

    Args:
        claim_id: Parent claim id.
        payload: Device data.
        db: Async DB session.
    """
    cd = await crud_claims.create_claim_device(
        db,
        claim_id=claim_id,
        device_id=payload.device_id,
        event_id=payload.event_id,
        oem_serial_number=payload.oem_serial_number,
        oem_part_number=payload.oem_part_number,
        notes=payload.notes,
    )
    return interfaces.ClaimDeviceResponse.model_validate(cd)


@router.patch(
    "/{claim_id}/devices/{claim_device_id}",
    response_model=interfaces.ClaimDeviceResponse,
)
async def patch_claim_device(
    claim_id: int,
    claim_device_id: int,
    payload: interfaces.ClaimDeviceUpdate,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """Update fields on a claim device.

    Args:
        claim_id: Claim id from route path.
        claim_device_id: PK of the claim device.
        payload: Updated device fields.
        db: Async DB session.
    """
    cd = await crud_claims.update_claim_device(
        db,
        claim_id=claim_id,
        claim_device_id=claim_device_id,
        device_id=payload.device_id,
        event_id=payload.event_id,
        oem_serial_number=payload.oem_serial_number,
        oem_part_number=payload.oem_part_number,
        notes=payload.notes,
    )
    if cd is None:
        raise HTTPException(
            status_code=404,
            detail="Claim device not found",
        )
    return interfaces.ClaimDeviceResponse.model_validate(cd)


@router.delete(
    "/{claim_id}/devices/{claim_device_id}",
    status_code=204,
)
async def remove_claim_device(
    claim_id: int,
    claim_device_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """Remove a device from a claim.

    Args:
        claim_id: Claim id from route path.
        claim_device_id: PK of the claim device.
        db: Async DB session.
    """
    deleted = await crud_claims.delete_claim_device(
        db,
        claim_id=claim_id,
        claim_device_id=claim_device_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Claim device not found",
        )


# ── Claim updates (timeline) ──


@router.post(
    "/{claim_id}/updates",
    response_model=interfaces.ClaimUpdateResponse,
    status_code=201,
)
async def add_claim_update(
    claim_id: int,
    payload: interfaces.ClaimUpdateCreate,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
):
    """Record a claim update.

    Args:
        claim_id: Parent claim id.
        payload: Update data.
        db: Async DB session.
        user: Authenticated user.
    """
    if (
        payload.update_type == enumerations.ClaimUpdateType.STATUS_CHANGE
        and payload.to_status
    ):
        await crud_claims.update_claim(
            db,
            claim_id=claim_id,
            status=payload.to_status,
        )

    cu = await crud_claims.create_claim_update(
        db,
        claim_id=claim_id,
        user_id=user.user_id,
        update_type=payload.update_type,
        from_status=payload.from_status,
        to_status=payload.to_status,
        message=payload.message,
        created_at=payload.created_at,
    )
    return interfaces.ClaimUpdateResponse.model_validate(cu)


# ── Claim attachments ──


@router.get(
    "/{claim_id}/attachments",
    response_model=list[interfaces.ClaimAttachmentInterface],
)
async def get_attachments(
    claim_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """List attachments for a claim.

    Args:
        claim_id: Claim id.
        db: Project-scoped async DB session.
    """
    rows = await claim_attachments.get_claim_attachments(
        db=db,
        claim_id=claim_id,
    )
    return [interfaces.ClaimAttachmentInterface(**r) for r in rows]


@router.post(
    "/{claim_id}/attachments",
    response_model=interfaces.ClaimAttachmentInterface,
    status_code=201,
)
async def upload_attachment(
    project_id: UUID,
    claim_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    file: UploadFile,
    claim_update_id: Annotated[int | None, Form()] = None,
):
    """Upload an attachment for a claim.

    Args:
        project_id: Project UUID.
        claim_id: Claim id.
        db: Project-scoped async DB session.
        file: Uploaded file.
        claim_update_id: Optional update to associate the attachment with.
    """
    schema = await dependencies.get_project_name_short_async(project_id=project_id)
    content = await file.read()
    row = await claim_attachments.add_claim_attachment(
        db=db,
        project_schema=schema or "",
        claim_id=claim_id,
        filename=file.filename or "unnamed",
        file_content=content,
        content_type=file.content_type,
        claim_update_id=claim_update_id,
    )
    return interfaces.ClaimAttachmentInterface(**row)


@router.delete(
    "/{claim_id}/attachments/{filename}",
    status_code=204,
)
async def delete_attachment(
    claim_id: int,
    filename: str,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
):
    """Delete an attachment.

    Args:
        claim_id: Claim id.
        filename: Name of the file to remove.
        db: Project-scoped async DB session.
    """
    deleted = await claim_attachments.delete_claim_attachment(
        db=db,
        claim_id=claim_id,
        filename=filename,
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Attachment not found",
        )


# ── Submit claim ──


@router.post("/{claim_id}/submit", status_code=200)
async def submit_claim(
    project_id: UUID,
    claim_id: int,
    db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    user: Annotated[
        interfaces.UserAuthed,
        Depends(authentication.get_user),
    ],
    payload: Annotated[
        interfaces.ClaimSubmit | None,
        Body(),
    ] = None,
):
    """Submit a draft claim: update status and email.

    Args:
        project_id: Project UUID.
        claim_id: Claim id.
        payload: Optional email subject/body and CC/BCC overrides.
        db: Async DB session.
        user: Authenticated user data.
    """
    claim_query = project_claims.query_claim(claim_id=claim_id)
    claim = cast(
        models.Claim | None,
        await claim_query.get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        ),
    )
    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found",
        )
    if claim.status != enumerations.ClaimStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft claims can be submitted",
        )

    old_status = claim.status
    await crud_claims.update_claim(
        db,
        claim_id=claim_id,
        status=enumerations.ClaimStatus.SUBMITTED,
    )
    await crud_claims.create_claim_update(
        db,
        claim_id=claim_id,
        user_id=user.user_id,
        update_type=enumerations.ClaimUpdateType.SUBMISSION,
        from_status=old_status,
        to_status=enumerations.ClaimStatus.SUBMITTED,
        message="Claim submitted",
    )

    config = claim.claim_config
    counterparty_name = "OEM"
    if config and config.counterparty_company:
        counterparty_name = config.counterparty_company.name_long or "OEM"

    opts = payload or interfaces.ClaimSubmit()

    to_emails_resolved = _resolve_claim_submit_to_emails(
        config=config,
        submit_opts=opts,
    )
    if to_emails_resolved and opts.email_body and opts.email_body.strip():
        try:
            project_result = await db.execute(
                sa.select(models.Project.name_long).where(
                    models.Project.project_id == project_id
                )
            )
            project_name = project_result.scalar() or "Project"
            sender_result = await db.execute(
                sa.select(
                    models.User.name_long,
                    models.Company.name_long,
                    models.Company.name_short,
                )
                .join(
                    models.Company,
                    models.User.company_id == models.Company.company_id,
                )
                .where(models.User.user_id == user.user_id)
            )
            sender_row = sender_result.one_or_none()
            sender_name = sender_row[0] if sender_row and sender_row[0] else ""
            sender_company = (
                (sender_row[1] or sender_row[2]) if sender_row is not None else ""
            )

            default_subject = (
                f"Warranty Claim #{claim_id} — {counterparty_name} — {project_name}"
            )
            subject = (
                opts.email_subject.strip()
                if opts.email_subject and opts.email_subject.strip()
                else default_subject
            )

            cc_list = opts.cc_emails or []
            bcc_list = opts.bcc_emails or []
            attachments = await claim_attachments.get_claim_attachment_files(
                db=db,
                claim_id=claim_id,
            )
            attachment_filenames = [
                str(attachment.get("filename") or "attachment")
                for attachment in attachments
            ]
            html_body = build_claim_submission_email_html(
                text=opts.email_body.strip(),
                project_name=project_name,
                claim_id=claim_id,
                counterparty_name=counterparty_name,
                sender_company=sender_company,
                attachment_filenames=attachment_filenames,
            )

            await send_claim_submission_email(
                to_emails=to_emails_resolved,
                cc_emails=cc_list,
                bcc_emails=bcc_list,
                subject=subject,
                html_body=html_body,
                sender_name=sender_name,
                sender_company=sender_company,
                attachments=attachments,
            )
        except Exception:
            logger.exception(
                "Failed to send claim email for claim %s to %s",
                claim_id,
                ", ".join(to_emails_resolved),
            )

    return {"status": "submitted", "claim_id": claim_id}
