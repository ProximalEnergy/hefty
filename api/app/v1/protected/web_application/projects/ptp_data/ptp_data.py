"""PTP Data endpoints for PowerTools Platform API data."""

from __future__ import annotations

import datetime
import logging
from typing import Annotated, TypedDict

from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, utils
from app._dependencies.authentication import get_user
from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import TokenManager
from app.interfaces import UserAuthed
from core import crud, models

router = APIRouter(
    prefix="/ptp-data",
    tags=["ptp-data"],
    include_in_schema=utils.get_include_in_schema(),
)

logger = logging.getLogger(__name__)

_REQUIRED_PTP_KEYS = (
    "cop_id",
    "entity_id",
    "resource_id",
    "generator_id",
    "settlement_point_id",
)


class PtpIdentifiers(TypedDict):
    """PTP identifiers from QSE integration provider_config."""

    cop_id: str
    entity_id: str
    resource_id: str
    generator_id: str
    settlement_point_id: str


def _get_ptp_identifiers(
    *,
    qse_integration: models.QSEIntegration,
) -> PtpIdentifiers:
    """Extract PTP identifiers from QSE integration provider_config.

    Args:
        qse_integration: QSE integration with provider_config JSONB.

    Returns:
        Dict with cop_id, entity_id, resource_id, generator_id, settlement_point_id.

    Raises:
        HTTPException: 400 if provider_config missing or incomplete.
    """
    cfg = qse_integration.provider_config
    if not cfg or not isinstance(cfg, dict):
        raise HTTPException(
            status_code=400,
            detail="QSE integration has no provider_config",
        )
    missing = [k for k in _REQUIRED_PTP_KEYS if not cfg.get(k)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"provider_config missing keys: {missing}",
        )
    return PtpIdentifiers(
        cop_id=str(cfg["cop_id"]),
        entity_id=str(cfg["entity_id"]),
        resource_id=str(cfg["resource_id"]),
        generator_id=str(cfg["generator_id"]),
        settlement_point_id=str(cfg["settlement_point_id"]),
    )


# Endpoint categories based on PTP_API_STRUCTURE_EXPLANATION.md
ENDPOINT_CATEGORIES = {
    "performance": [
        "Generator-Performance",
        "Load-Performance",
        "Controllable-Load-Performance",
    ],
    "settlement": [
        "Settlement-Charges",
        "Settlement-Charge-Details",
        "Day-Ahead-Settlement-Amounts",
        "Real-Time-Settlement-Amounts",
        "Settlement-Summary",
        "Settlement-Charges-Sequenced",
        "Estimated-Settlement-Amounts",
        "BPDAMT-Summary",
        "EnergySettlement",
        "Day_Ahead_Daily_Settlement",
    ],
    "market": [
        "Market-Prices",
        "ERCOT-Statement-Values",
        "Market-Settlement-Values",
        "System_Load_Data",
        "System_Wind_Data",
        "System-Solar-Data",
    ],
    "analysis": [
        "DART-Energy-Details",
        "Configuration-Awards",
        "Real-Time-Unit-Position",
        "MktInput-5Min",
        "Customer_Position",
        "Bilateral-Transaction-Details",
    ],
    "submissions": [
        "Submissions-Current-Operating-Plan",
        "Submissions-Telemetered-Current-Operating-Plan",
        "Submissions-DA-Energy-Bid",
        "Submissions-DA-Energy-Only-Offer",
        "Submissions-Availability-Plan",
        "Submissions-AS-Offer-DA",
        "Submissions-AS-Offer-RT",
        "Submissions-Three-Part-Offer-DA",
        "Submissions-Three-Part-Offer-RT",
        "Submissions-Output-Schedule",
        "Submissions-Self-Schedule",
        "Submissions-PTP-Bid",
        "Submissions-RTM-Energy-Bid",
    ],
}


async def _check_endpoint_has_data(
    *,
    token: str,
    endpoint: str,
    element_id: str,
    days_back: int = 7,
) -> bool:
    """Check if an endpoint has data for the given element.

    Args:
        token: Bearer token for authentication.
        endpoint: Endpoint name.
        element_id: Element identifier.
        days_back: Number of days to look back for data.

    Returns:
        True if data exists, False otherwise.
    """
    try:
        now = datetime.datetime.now(datetime.UTC)
        begin = (
            (now - datetime.timedelta(days=days_back))
            .isoformat()
            .replace("+00:00", "Z")
        )
        end = (now + datetime.timedelta(hours=2)).isoformat().replace("+00:00", "Z")

        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[element_id],
            begin=begin,
            end=end,
        )

        # Check if we have data with actual values
        if "data" in result and result["data"]:
            for element_data in result["data"]:
                if "dataPoints" in element_data:
                    for dp in element_data["dataPoints"]:
                        if "values" in dp and dp["values"]:
                            # Check if any value has actual data (not just nulls)
                            for value_obj in dp["values"]:
                                if "data" in value_obj and value_obj["data"]:
                                    for data_point in value_obj["data"]:
                                        if (
                                            "value" in data_point
                                            and data_point["value"] is not None
                                        ):
                                            return True
        return False
    except Exception:
        # If there's an error, assume no data
        return False


@router.get("/endpoints")
async def get_ptp_endpoints_route(
    user: Annotated[UserAuthed, Depends(get_user)],
    project: models.Project = Depends(dependencies.get_project_api),
    _tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get available PTP endpoints organized by category.

    Args:
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        user: User model provided by dependency injection.
        db_async: Database session.

    Returns:
        Dictionary of endpoints organized by category.
    """
    # Get QSE integration
    qse_integration_query = (
        crud.operational.qse_integrations.get_qse_integration_by_project_id(
            project_id=project.project_id,
        )
    )
    qse_integration = await qse_integration_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise HTTPException(status_code=404, detail="QSE integration not found")

    # Check permissions
    permissions_query = (
        crud.operational.qse_integrations.get_qse_permissions_by_company_id(
            company_id=user.company_id,
        )
    )
    permissions = await permissions_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    has_permission = any(
        perm.qse_integration_id == qse_integration.qse_integration_id and perm.can_view
        for perm in permissions
    )
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="No QSE permissions for this project"
        )

    try:
        ids = _get_ptp_identifiers(qse_integration=qse_integration)
        return {
            "categories": ENDPOINT_CATEGORIES,
            "identifiers": {
                "generator_id": ids["generator_id"],
                "entity_id": ids["entity_id"],
                "resource_id": ids["resource_id"],
                "settlement_point_id": ids["settlement_point_id"],
                "cop_id": ids["cop_id"],
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to get endpoints: {exc}"
        ) from exc


@router.get("/endpoints/availability")
async def get_ptp_endpoints_availability(
    user: Annotated[UserAuthed, Depends(get_user)],
    category: str = Query(..., description="Category to check availability for"),
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Check data availability for endpoints in a specific category.

    Args:
        category: Category name (performance, settlement, market, etc.).
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        user: User model provided by dependency injection.
        db_async: Database session.

    Returns:
        Dictionary mapping endpoint names to availability booleans.
    """
    # Get QSE integration
    qse_integration_query = (
        crud.operational.qse_integrations.get_qse_integration_by_project_id(
            project_id=project.project_id,
        )
    )
    qse_integration = await qse_integration_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise HTTPException(status_code=404, detail="QSE integration not found")

    # Check permissions
    permissions_query = (
        crud.operational.qse_integrations.get_qse_permissions_by_company_id(
            company_id=user.company_id,
        )
    )
    permissions = await permissions_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    has_permission = any(
        perm.qse_integration_id == qse_integration.qse_integration_id and perm.can_view
        for perm in permissions
    )
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="No QSE permissions for this project"
        )

    # Validate category
    if category not in ENDPOINT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    try:
        ids = _get_ptp_identifiers(qse_integration=qse_integration)
        token = await tps_token.get_token()

        # Check data availability for endpoints in this category
        endpoint_availability: dict[str, bool] = {}
        endpoints = ENDPOINT_CATEGORIES.get(category, [])

        for endpoint in endpoints:
            # Mirror get_ptp_data element selection (settlement-point for Market-Prices)
            if endpoint == "Market-Prices":
                element_id = ids["settlement_point_id"]
            elif "Generator" in endpoint or "Real-Time-Unit-Position" in endpoint:
                element_id = ids["generator_id"]
            else:
                element_id = ids["entity_id"]

            has_data = await _check_endpoint_has_data(
                token=token,
                endpoint=endpoint,
                element_id=element_id,
            )
            endpoint_availability[endpoint] = has_data

        return endpoint_availability
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to check availability: {exc}"
        ) from exc


@router.get("/data")
async def get_ptp_data(
    user: Annotated[UserAuthed, Depends(get_user)],
    endpoint: str = Query(..., description="PTP endpoint name"),
    category: str = Query(..., description="Endpoint category"),
    start: datetime.datetime | None = Query(
        None, description="Start datetime (ISO 8601 UTC)"
    ),
    end: datetime.datetime | None = Query(
        None, description="End datetime (ISO 8601 UTC)"
    ),
    element_id: str | None = Query(
        None, description="Element identifier (defaults from provider_config)"
    ),
    data_points: Annotated[list[str] | None, Query()] = None,
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get PTP data for a specific endpoint.

    Args:
        endpoint: PTP endpoint name (e.g., "Generator-Performance").
        category: Endpoint category (performance, settlement, market, etc.).
        start: Optional start datetime (ISO 8601 UTC).
        end: Optional end datetime (ISO 8601 UTC).
        element_id: Optional element identifier (defaults from provider_config).
        data_points: Optional list of data point keynames to filter.
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        user: User model provided by dependency injection.
        db_async: Database session.

    Returns:
        PTP endpoint data.
    """
    # Get QSE integration
    qse_integration_query = (
        crud.operational.qse_integrations.get_qse_integration_by_project_id(
            project_id=project.project_id,
        )
    )
    qse_integration = await qse_integration_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise HTTPException(status_code=404, detail="QSE integration not found")

    # Check permissions
    permissions_query = (
        crud.operational.qse_integrations.get_qse_permissions_by_company_id(
            company_id=user.company_id,
        )
    )
    permissions = await permissions_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    has_permission = any(
        perm.qse_integration_id == qse_integration.qse_integration_id and perm.can_view
        for perm in permissions
    )
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="No QSE permissions for this project"
        )

    if category not in ENDPOINT_CATEGORIES:
        logger.debug("Unknown PTP category: %s", category)

    ids = _get_ptp_identifiers(qse_integration=qse_integration)

    # Special handling for COP endpoints - need to find the right identifier
    is_cop_endpoint = "Current-Operating-Plan" in endpoint or "COP" in endpoint

    # Format dates: normalize to UTC and format once (no double timezone marker)
    def _to_iso_utc(*, dt: datetime.datetime) -> str:
        utc = dt.astimezone(datetime.UTC) if dt.tzinfo else dt
        s = utc.isoformat().replace("+00:00", "Z")
        return s if s.endswith("Z") else s + "Z"

    begin_str = _to_iso_utc(dt=start) if start else None
    end_str = _to_iso_utc(dt=end) if end else None
    requested_data_points = list(data_points) if data_points else None

    try:
        token = await tps_token.get_token()

        # For COP endpoints, choose primary identifier by endpoint.
        # RTC uses generator_id (per Submissions-Current-Operating-Plan-RTC endpoint
        # analysis); non-RTC uses cop_id.
        if is_cop_endpoint and element_id is None:
            is_rtc_cop = endpoint == "Submissions-Current-Operating-Plan-RTC"
            primary_id = ids["generator_id"] if is_rtc_cop else ids["cop_id"]
            element_id = primary_id

            # Verify it has data by querying it
            try:
                test_data = await ptp_explorer.get_endpoint_data(
                    token=token,
                    market="ERCOTNodal",
                    endpoint=endpoint,
                    elements=[primary_id],
                    begin=begin_str,
                    end=end_str,
                )

                # Check if we got actual time-series data (not just Resource_ID)
                has_time_series = False
                test_entries = test_data.get("data")
                if isinstance(test_entries, list) and test_entries:
                    for entry in test_entries:
                        if not isinstance(entry, dict):
                            continue
                        if entry.get("identifier") == primary_id:
                            entry_data_points = entry.get("dataPoints", [])
                            if not isinstance(entry_data_points, list):
                                break
                            for dp in entry_data_points:
                                if not isinstance(dp, dict):
                                    continue
                                key_name = str(dp.get("keyName", ""))
                                if key_name != "Resource_ID":
                                    values = dp.get("values", [])
                                    if not isinstance(values, list):
                                        continue
                                    for val in values:
                                        if isinstance(val, dict):
                                            interval = val.get("intervalStartUtc", "")
                                            # Check for real timestamps (not placeholder
                                            # dates).
                                            if (
                                                interval
                                                and "1753" not in interval
                                                and "1900" not in interval
                                            ):
                                                try:
                                                    parsed_date = (
                                                        datetime.datetime.fromisoformat(
                                                            interval.replace(
                                                                "Z", "+00:00"
                                                            )
                                                        )
                                                    )
                                                    if (
                                                        parsed_date.year >= 2015
                                                        and parsed_date.year <= 2030
                                                    ):
                                                        has_time_series = True
                                                        break
                                                except Exception:
                                                    logger.debug(
                                                        "Failed to parse interval",
                                                        exc_info=True,
                                                    )
                                    if has_time_series:
                                        break
                            break

                # If no time-series data, fall back to searching all identifiers
                if not has_time_series:
                    # Query all COP data to find identifier matching project config
                    all_cop_data = await ptp_explorer.get_endpoint_data(
                        token=token,
                        market="ERCOTNodal",
                        endpoint=endpoint,
                        elements=None,  # No filter to get all
                        begin=begin_str,
                        end=end_str,
                    )

                    # Find identifier matching project resource_id with COP data
                    all_entries = all_cop_data.get("data")
                    if isinstance(all_entries, list) and all_entries:
                        best_identifier = None
                        max_intervals = 0

                        for entry in all_entries:
                            if not isinstance(entry, dict):
                                continue
                            entry_id = entry.get("identifier")
                            entry_data_points = entry.get("dataPoints", [])
                            if not isinstance(entry_data_points, list):
                                continue
                            resource_id = None

                            # Extract Resource_ID
                            for dp in entry_data_points:
                                if not isinstance(dp, dict):
                                    continue
                                if dp.get("keyName") == "Resource_ID":
                                    values = dp.get("values", [])
                                    if not isinstance(values, list):
                                        continue
                                    for val in values:
                                        if isinstance(val, dict):
                                            value_data = val.get("data", [])
                                            if value_data and len(value_data) > 0:
                                                resource_id = str(
                                                    value_data[0].get("value", "")
                                                )
                                                break
                                    break

                            # Check if this matches project resource_id from config
                            if resource_id and resource_id == ids["resource_id"]:
                                # Check if this entry has actual COP data (not just
                                # Resource_ID).
                                interval_count = 0
                                for dp in entry_data_points:
                                    if not isinstance(dp, dict):
                                        continue
                                    key_name = str(dp.get("keyName", ""))
                                    if key_name != "Resource_ID":
                                        values = dp.get("values", [])
                                        if not isinstance(values, list):
                                            continue
                                        for val in values:
                                            if isinstance(val, dict):
                                                interval = val.get(
                                                    "intervalStartUtc", ""
                                                )
                                                # Filter out placeholder dates
                                                if (
                                                    interval
                                                    and "1753" not in interval
                                                    and "1900" not in interval
                                                ):
                                                    try:
                                                        parsed_interval = (
                                                            interval.replace(
                                                                "Z",
                                                                "+00:00",
                                                            )
                                                        )
                                                        parsed_date = datetime.datetime.fromisoformat(  # noqa: E501
                                                            parsed_interval
                                                        )
                                                        if (
                                                            parsed_date.year >= 2015
                                                            and parsed_date.year <= 2030
                                                        ):
                                                            interval_count += 1
                                                            break
                                                    except Exception:
                                                        logger.debug(
                                                            "Failed to parse interval",
                                                            exc_info=True,
                                                        )
                                        if interval_count > 0:
                                            break

                                if interval_count > max_intervals:
                                    max_intervals = interval_count
                                    best_identifier = entry_id

                        # Use the best identifier found, or keep cop_id as default
                        if best_identifier:
                            element_id = best_identifier
            except Exception:
                # If verification fails, keep cop_id as default
                logger.debug("COP identifier verification failed", exc_info=True)
        else:
            # Determine which element ID to use based on endpoint
            # Only set default if element_id was not explicitly provided
            if element_id is None:
                # Use settlement point ID for Market-Prices endpoint
                if endpoint == "Market-Prices":
                    element_id = ids["settlement_point_id"]
                # Use generator ID for generator-specific endpoints
                elif "Generator" in endpoint or "Real-Time-Unit-Position" in endpoint:
                    element_id = ids["generator_id"]
                # Use entity ID for most other endpoints
                else:
                    element_id = ids["entity_id"]

        # Now query with the determined element_id
        # Always pass element_id to filter results (more efficient than fetching all)
        logger.info(
            f"Querying PTP endpoint '{endpoint}' with element_id={element_id}, "
            f"begin={begin_str}, end={end_str}"
        )

        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[element_id] if element_id else None,
            begin=begin_str,
            end=end_str,
            data_points=requested_data_points,
        )

        # For COP endpoints, filter out placeholder dates from the response
        if is_cop_endpoint and "data" in result:
            entries = result.get("data")
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    entry_data_points = entry.get("dataPoints", [])
                    if not isinstance(entry_data_points, list):
                        continue
                    for dp in entry_data_points:
                        if not isinstance(dp, dict):
                            continue
                        values = dp.get("values", [])
                        if not isinstance(values, list):
                            continue
                        # Filter out values with placeholder dates
                        if values:
                            filtered_values = []
                            for val in values:
                                if isinstance(val, dict):
                                    interval = val.get("intervalStartUtc", "")
                                    # Keep only real dates
                                    if (
                                        interval
                                        and "1753" not in interval
                                        and "1900" not in interval
                                    ):
                                        try:
                                            parsed_date = (
                                                datetime.datetime.fromisoformat(
                                                    interval.replace("Z", "+00:00")
                                                )
                                            )
                                            if (
                                                parsed_date.year >= 2015
                                                and parsed_date.year <= 2030
                                            ):
                                                filtered_values.append(val)
                                        except Exception:
                                            # If parsing fails, keep it
                                            filtered_values.append(val)
                            dp["values"] = filtered_values

        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch PTP data: {exc}"
        ) from exc


async def _find_element_identifier_by_resource_name(
    *,
    token: str,
    market: str,
    endpoint: str,
    resource_name: str,
) -> str | None:
    """Find element identifier by querying without filters and searching by
    resource name.

    Args:
        token: Bearer token for authentication.
        market: Market name.
        endpoint: Endpoint name.
        resource_name: Resource name to search for.

    Returns:
        Element identifier if found, None otherwise.
    """
    try:
        now = datetime.datetime.now(datetime.UTC)
        begin = (now - datetime.timedelta(days=7)).isoformat().replace("+00:00", "Z")
        end = (now + datetime.timedelta(hours=2)).isoformat().replace("+00:00", "Z")

        data = await ptp_explorer.get_endpoint_data(
            token=token,
            market=market,
            endpoint=endpoint,
            elements=None,
            begin=begin,
            end=end,
        )

        if "data" in data and data["data"]:
            entries = data.get("data")
            if not isinstance(entries, list):
                return None

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                element_name = str(entry.get("element", ""))
                identifier = entry.get("identifier")
                definition = str(entry.get("definition", ""))
                if not isinstance(identifier, str):
                    continue

                if (
                    element_name.upper() == resource_name.upper()
                    and definition == "Equipment"
                ):
                    return identifier

            # Try partial match
            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                element_name = str(entry.get("element", ""))
                identifier = entry.get("identifier")
                definition = str(entry.get("definition", ""))
                if not isinstance(identifier, str):
                    continue

                if (
                    resource_name.upper() in element_name.upper()
                    and definition == "Equipment"
                ):
                    return identifier

        return None
    except Exception:
        return None


def _determine_ticket_status(*, ticket: dict) -> bool:
    """Determine if a ticket is active based on its data points.

    A ticket is considered active if:
    1. It's not closed/cancelled/completed
    2. It doesn't have an actual end time
    3. Today's date falls within the planned start and end date range

    Args:
        ticket: Ticket data with data_points dictionary.

    Returns:
        True if ticket is active, False otherwise.
    """
    data_points = ticket.get("data_points", {})
    now = datetime.datetime.now(datetime.UTC)

    # Check OutageStatus
    outage_status = data_points.get("OutageStatus")
    if outage_status:
        status_upper = str(outage_status).upper()
        if status_upper in ["CLOSED", "COMPLETED", "CANCELLED"]:
            return False

    # Check ActualEndTime - if it exists, ticket is closed
    actual_end_time = data_points.get("ActualEndTime")
    if actual_end_time:
        return False

    # Check if today falls within planned start and end range
    planned_start_time = data_points.get("PlannedStartTime")
    planned_end_time = data_points.get("PlannedEndTime")

    # If we have both start and end times, we MUST check if today is within
    # range. This is the primary criteria - if both dates exist, only count if
    # today is between them.
    if planned_start_time and planned_end_time:
        try:
            if isinstance(planned_start_time, str) and isinstance(
                planned_end_time, str
            ):
                # Handle timezone-aware strings
                start_str = planned_start_time.replace("Z", "+00:00")
                end_str = planned_end_time.replace("Z", "+00:00")

                start_dt = datetime.datetime.fromisoformat(start_str)
                end_dt = datetime.datetime.fromisoformat(end_str)

                # Ensure timezone-aware
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=datetime.UTC)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=datetime.UTC)

                # Ticket is active ONLY if today is between start and end (inclusive)
                is_in_range = start_dt <= now <= end_dt
                return is_in_range
        except Exception as e:
            # If we can't parse the dates, we can't determine if it's active
            # Log the error and return False to be safe
            logger.warning(
                f"Failed to parse planned dates for ticket: {e}. "
                f"Start: {planned_start_time}, End: {planned_end_time}"
            )
            return False

    # If we only have end time (no start), check if it's in the future
    if planned_end_time and not planned_start_time:
        try:
            if isinstance(planned_end_time, str):
                end_str = planned_end_time.replace("Z", "+00:00")
                end_dt = datetime.datetime.fromisoformat(end_str)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=datetime.UTC)
                # Only active if end is in the future
                return end_dt > now
        except Exception:
            return False

    # If we only have start time (no end), check if it's in the past
    if planned_start_time and not planned_end_time:
        try:
            if isinstance(planned_start_time, str):
                start_str = planned_start_time.replace("Z", "+00:00")
                start_dt = datetime.datetime.fromisoformat(start_str)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=datetime.UTC)
                # Only active if start is in the past
                return start_dt <= now
        except Exception:
            return False

    # If no planned times at all, default to False (not active)
    # We require planned dates to determine if a ticket is active
    return False


@router.get("/active-outage-tickets")
async def get_active_outage_tickets(
    user: Annotated[UserAuthed, Depends(get_user)],
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
    resource_name: str | None = Query(
        default=None,
        description="Resource name to query (default: from provider_config)",
    ),
):
    """Get count of active outage tickets for a resource.

    Args:
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        user: User model provided by dependency injection.
        db_async: Database session.
        resource_name: Resource name to query (default: from provider_config).

    Returns:
        Dictionary with active_tickets count.
    """
    # Get QSE integration
    qse_integration_query = (
        crud.operational.qse_integrations.get_qse_integration_by_project_id(
            project_id=project.project_id,
        )
    )
    qse_integration = await qse_integration_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise HTTPException(status_code=404, detail="QSE integration not found")

    # Check permissions
    permissions_query = (
        crud.operational.qse_integrations.get_qse_permissions_by_company_id(
            company_id=user.company_id,
        )
    )
    permissions = await permissions_query.get_async(
        executor=db_async,
        output_type=OutputType.SQLALCHEMY,
    )
    has_permission = any(
        perm.qse_integration_id == qse_integration.qse_integration_id and perm.can_view
        for perm in permissions
    )
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="No QSE permissions for this project"
        )

    ids = _get_ptp_identifiers(qse_integration=qse_integration)
    resource_name_to_use = (
        resource_name if resource_name is not None else ids["resource_id"]
    )

    try:
        token = await tps_token.get_token()

        # Find element identifier for the resource
        element_identifier = await _find_element_identifier_by_resource_name(
            token=token,
            market="Operations",
            endpoint="Outage-Ticket-Data-ERCOT",
            resource_name=resource_name_to_use,
        )

        if not element_identifier:
            # No element found for this resource; return empty to avoid wrong
            # counts or leaking another project's outage data.
            return {"active_tickets": 0, "tickets": []}

        # Query tickets
        now = datetime.datetime.now(datetime.UTC)
        begin = (now - datetime.timedelta(days=30)).isoformat().replace("+00:00", "Z")
        end = (now + datetime.timedelta(days=30)).isoformat().replace("+00:00", "Z")

        data = await ptp_explorer.get_endpoint_data(
            token=token,
            market="Operations",
            endpoint="Outage-Ticket-Data-ERCOT",
            elements=[element_identifier],
            begin=begin,
            end=end,
        )

        if "data" not in data or not data["data"]:
            return {"active_tickets": 0, "tickets": []}

        # Process all ticket items and determine status
        all_tickets = []
        active_count = 0
        for entry in data["data"]:
            definition = entry.get("definition", "")
            if definition != "Ticket Item":
                continue

            # Extract data point values
            ticket_data_points = {}
            for dp in entry.get("dataPoints", []):
                key_name = dp.get("keyName")
                values = dp.get("values", [])

                if values:
                    for val in values:
                        data_array = val.get("data", [])
                        if data_array and len(data_array) > 0:
                            ticket_data_points[key_name] = data_array[0].get("value")
                            break

            ticket = {
                "identifier": entry.get("identifier"),
                "element": entry.get("element", ""),
                "data_points": ticket_data_points,
            }
            is_active = _determine_ticket_status(ticket=ticket)
            if is_active:
                active_count += 1

            # Format ticket for response (include all tickets, not just active)
            all_tickets.append(
                {
                    "identifier": ticket["identifier"],
                    "element": ticket["element"],
                    "outage_status": ticket_data_points.get("OutageStatus"),
                    "planned_start_time": ticket_data_points.get("PlannedStartTime"),
                    "planned_end_time": ticket_data_points.get("PlannedEndTime"),
                    "actual_end_time": ticket_data_points.get("ActualEndTime"),
                    "station": ticket_data_points.get("Station"),
                    "resource_id": ticket_data_points.get("ResourceID"),
                    "data_points": ticket_data_points,  # Include all data points
                    "go_live_date": entry.get("goLiveDate"),
                    "expiration_date": entry.get("expirationDate"),
                    "parent_identifier": entry.get("parentIdentifier"),
                    # Flag to indicate if ticket is currently active
                    "is_active": is_active,
                }
            )

        return {"active_tickets": active_count, "tickets": all_tickets}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch active outage tickets: {exc}"
        ) from exc
