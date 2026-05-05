"""Market Performance endpoints for real-time market data."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import pandas as pd
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

import core
from app import dependencies, utils
from app._dependencies.authentication import get_user
from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import TokenManager
from app.interfaces import UserAuthed
from app.v1.protected.web_application.projects.ptp_data.ptp_data import (
    _get_ptp_identifiers,
)
from core import models

router = APIRouter(
    prefix="/market-performance",
    tags=["market-performance"],
    include_in_schema=utils.get_include_in_schema(),
)

logger = logging.getLogger(__name__)


def _extract_resource_id(*, entry: dict[str, Any]) -> str | None:
    data_points = entry.get("dataPoints", [])
    if not isinstance(data_points, list):
        return None

    for dp in data_points:
        if not isinstance(dp, dict):
            continue
        if dp.get("keyName") != "Resource_ID":
            continue

        values = dp.get("values", [])
        if not isinstance(values, list):
            return None

        for val in values:
            if not isinstance(val, dict):
                continue
            value_data = val.get("data", [])
            if value_data and isinstance(value_data, list) and len(value_data) > 0:
                first = value_data[0]
                if isinstance(first, dict):
                    resource_id = first.get("value")
                    return str(resource_id) if resource_id is not None else None
        return None

    return None


def _entries_have_resource_id(*, entries: list[dict[str, Any]]) -> bool:
    return any(_extract_resource_id(entry=e) for e in entries)


def _entries_have_generator_configuration(*, entries: list[dict[str, Any]]) -> bool:
    # PTP docs use "Generator Configuration" for resource-level config items.
    for e in entries:
        definition = e.get("definition")
        if isinstance(definition, str) and definition == "Generator Configuration":
            return True
    return False


async def _safe_fetch_ptp_endpoint_data(
    *,
    token: str,
    endpoint: str,
    parent_identifier: str,
    begin: str,
    end: str,
) -> dict[str, Any] | None:
    try:
        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[parent_identifier],
            begin=begin,
            end=end,
        )
        return result if isinstance(result, dict) else None
    except Exception:
        logger.debug("Failed to fetch %s identifiers", endpoint, exc_info=True)
        return None


def _project_tzinfo(*, tz: str | None) -> datetime.tzinfo:
    if not tz:
        return datetime.UTC
    try:
        return ZoneInfo(tz)
    except Exception:
        return datetime.UTC


@router.get("/has-access")
async def check_qse_access(
    user: Annotated[UserAuthed, Depends(get_user)],
    project: models.Project = Depends(dependencies.get_project_api),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
) -> dict[str, bool]:
    """Check if user has QSE market access for a project.

    Returns whether the project has a QSE integration and
    the user's company has the corresponding QSE permission.

    Args:
        project: Project from dependency injection.
        user: Authenticated user from dependency injection.
        db_async: Async database session.
    """
    has_access_query = select(
        exists().where(
            and_(
                models.QSEIntegration.project_id == project.project_id,
                models.QSEPermission.qse_integration_id
                == models.QSEIntegration.qse_integration_id,
                models.QSEPermission.company_id == user.company_id,
                models.QSEPermission.can_view.is_(True),
            )
        )
    )
    result = await db_async.execute(has_access_query)
    has_access = result.scalar_one()
    return {"has_access": has_access}


@router.get("/debug/raw")
async def get_market_performance_debug_raw(
    user: Annotated[UserAuthed, Depends(get_user)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Debug endpoint to return raw PTP API response.

    This helps understand the actual structure of data returned from PTP.
    """
    # Get QSE integration
    qse_integration_query = (
        core.crud.operational.qse_integrations.get_qse_integration_by_project_id(
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
        core.crud.operational.qse_integrations.get_qse_permissions_by_company_id(
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
        raise HTTPException(status_code=403, detail="Forbidden")

    # Default to last 2 hours if not specified
    tz_str = project.time_zone
    if end is None:
        end = datetime.datetime.now(tz=_project_tzinfo(tz=tz_str))
    if start is None:
        start = end - datetime.timedelta(hours=2)

    # Convert to UTC for API
    start_ts = (
        pd.to_datetime(start).tz_localize(tz_str)
        if start.tzinfo is None
        else pd.to_datetime(start)
    )
    end_ts = (
        pd.to_datetime(end).tz_localize(tz_str)
        if end.tzinfo is None
        else pd.to_datetime(end)
    )
    begin_utc = start_ts.tz_convert("UTC")
    end_utc = end_ts.tz_convert("UTC")

    # Get token
    token = await tps_token.get_token()

    # Fetch data from PTP API (using new /ptp API structure)
    url = "https://api.ptp.energy/ptp/ERCOTNodal/Battery-Settlement-Details/query"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "begin": begin_utc.isoformat().replace("+00:00", "Z"),
        "end": end_utc.isoformat().replace("+00:00", "Z"),
        "elementIdentifiers": [qse_integration.qse_project_identifier],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch market data: {exc}",
        ) from exc

    # Return raw response with metadata
    return {
        "status_code": response.status_code,
        "identifier": qse_integration.qse_project_identifier,
        "params_used": params,
        "raw_response": payload,
        "data_entries_count": len(payload.get("data", [])),
        "data_point_keys": [
            dp.get("keyName")
            for entry in payload.get("data", [])
            for dp in entry.get("dataPoints", [])
        ]
        if payload.get("data")
        else [],
    }


@router.get("/realtime")
async def get_market_performance_realtime(
    user: Annotated[UserAuthed, Depends(get_user)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get real-time market performance data.

    Args:
        start: Optional start datetime (defaults to 2 hours ago).
        end: Optional end datetime (defaults to now).
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        user: User model provided by dependency injection.
        db_async: Database session.

    Returns:
        Real-time market performance data including telemetry, market prices,
        awards, and financial metrics.
    """
    # Get QSE integration
    qse_integration_query = (
        core.crud.operational.qse_integrations.get_qse_integration_by_project_id(
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
        core.crud.operational.qse_integrations.get_qse_permissions_by_company_id(
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
        raise HTTPException(status_code=403, detail="Forbidden")

    # Default to last 2 hours if not specified
    tz_str = project.time_zone
    if end is None:
        end = datetime.datetime.now(tz=_project_tzinfo(tz=tz_str))
    if start is None:
        start = end - datetime.timedelta(hours=2)

    # Convert to UTC for API
    start_ts = (
        pd.to_datetime(start).tz_localize(tz_str)
        if start.tzinfo is None
        else pd.to_datetime(start)
    )
    end_ts = (
        pd.to_datetime(end).tz_localize(tz_str)
        if end.tzinfo is None
        else pd.to_datetime(end)
    )
    begin_utc = start_ts.tz_convert("UTC")
    end_utc = end_ts.tz_convert("UTC")

    # Get token
    token = await tps_token.get_token()

    # Fetch data from PTP API using Battery-Settlement-Details endpoint.
    # This endpoint contains settlement data with financial + operational metrics.
    # Using new /ptp API structure.
    url = "https://api.ptp.energy/ptp/ERCOTNodal/Battery-Settlement-Details/query"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "begin": begin_utc.isoformat().replace("+00:00", "Z"),
        "end": end_utc.isoformat().replace("+00:00", "Z"),
        "elementIdentifiers": [qse_integration.qse_project_identifier],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch market data: {exc}",
        ) from exc

    payload = response.json()
    data = next(
        (
            entry
            for entry in payload.get("data", [])
            if entry.get("identifier") == qse_integration.qse_project_identifier
        ),
        None,
    )
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Identifier {qse_integration.qse_project_identifier} "
                "not found in market data"
            ),
        )

    # Parse data into DataFrame
    df = pd.DataFrame()
    for dp in data.get("dataPoints", []):
        temp = pd.DataFrame(dp.get("values", []))
        if temp.empty:
            continue
        temp["intervalStartUtc"] = pd.to_datetime(temp["intervalStartUtc"])
        temp["intervalEndUtc"] = pd.to_datetime(temp["intervalEndUtc"])
        temp["data"] = temp["data"].apply(
            lambda x: float(x[0]["value"]) if x and len(x) > 0 else None
        )
        temp = temp.set_index("intervalStartUtc")
        temp = temp.rename(columns={"data": dp["keyName"]}).drop(
            columns=["intervalEndUtc"], errors="ignore"
        )
        df = pd.concat([df, temp], axis=1)

    if df.empty:
        return {
            "telemetry": {},
            "market": {},
            "awards": {},
            "finance": {},
            "intervals": [],
        }

    # Convert index to project timezone
    df.index = df.index.tz_convert(project.time_zone)  # type: ignore
    df.index.name = "time"

    # Replace null-like values with None for JSON serialization
    df = df.replace({pd.NA: None, pd.NaT: None, np.nan: None})

    # Get field mappings
    fields = await core.crud.operational.qse_integrations.get_qse_fields_by_provider_id(
        db=db_async, provider_id=qse_integration.qse_provider_id
    )
    fields_df = core.utils.core_utils.model_list_to_pandas(model_list=fields).set_index(
        "qse_field_name"
    )

    # Replace null-like values with None for JSON serialization
    df = df.replace({pd.NA: None, pd.NaT: None, np.nan: None})

    # Map field names using the database mappings (same as battery_settlement)
    field_mapping = fields_df["name_long"].to_dict() if not fields_df.empty else {}
    df_renamed = df.rename(columns=field_mapping)

    # Get unit mappings
    unit_mapping = (
        fields_df.set_index("name_long")["unit"].to_dict()
        if not fields_df.empty
        else {}
    )

    # Get the name mapping (raw keyName -> friendly name) for calculations
    name = fields_df["name_long"].to_dict() if not fields_df.empty else {}

    # Calculate derived metrics similar to battery_settlement
    def s(*, col_name: str) -> pd.Series:
        """Safely fetch numeric series or return zero series.

        Args:
            col_name: Column name to look up in the renamed DataFrame.
        """
        return utils.get_numeric_series(df=df_renamed, col_name=col_name, fillna=0.0)

    # Calculate metrics
    calculated = pd.DataFrame(index=df_renamed.index)

    # Net Power = Generation - Consumption
    RT_GEN = name.get("RT_Generation_Qty", "RT_Generation_Qty")
    RT_CON = name.get("RT_Consumption_Qty", "RT_Consumption_Qty")
    if RT_GEN in df_renamed.columns or RT_CON in df_renamed.columns:
        calculated["Net Power (MW)"] = s(col_name=RT_GEN) - s(col_name=RT_CON)

    # Net Position (DA)
    DA_SALES = name.get("DA_Sales_Qty", "DA_Sales_Qty")
    DA_PURCH = name.get("DA_Purchases_Qty", "DA_Purchases_Qty")
    if DA_SALES in df_renamed.columns or DA_PURCH in df_renamed.columns:
        calculated["DA Net Position (MWh)"] = s(col_name=DA_SALES) - s(
            col_name=DA_PURCH
        )

    # Price spread
    RT_SPP = name.get("RTSPP_Avg", "RTSPP_Avg")
    DA_SPP = name.get("DASPP", "DASPP")
    if RT_SPP in df_renamed.columns and DA_SPP in df_renamed.columns:
        calculated["RT - DA Price Spread ($/MWh)"] = s(col_name=RT_SPP) - s(
            col_name=DA_SPP
        )

    # Financial metrics
    RT_EN_AMT = name.get("RT_Energy_Amt", "RT_Energy_Amt")
    DA_EN_AMT = name.get("DA_Energy_Amt", "DA_Energy_Amt")
    BP_DEV = name.get("BP_Dev_Amt", "BP_Dev_Amt")
    RT_AS_IMB = name.get("RT_Ancillary_Imbalance_Amt", "RT_Ancillary_Imbalance_Amt")

    # Net Profit calculation
    total_revenue = utils.create_zero_series(index=df_renamed.index)
    if RT_EN_AMT in df_renamed.columns:
        total_revenue += s(col_name=RT_EN_AMT)
    if DA_EN_AMT in df_renamed.columns:
        total_revenue += s(col_name=DA_EN_AMT)

    total_imbalance = utils.create_zero_series(index=df_renamed.index)
    if BP_DEV in df_renamed.columns:
        total_imbalance += s(col_name=BP_DEV)
    if RT_AS_IMB in df_renamed.columns:
        total_imbalance += s(col_name=RT_AS_IMB)

    calculated["Net Profit ($)"] = total_revenue + total_imbalance

    # Structure response
    intervals = [str(ts) for ts in df_renamed.index.tolist()]

    # Extract data by category - use both mapped names and original keyNames
    telemetry_data = {}
    # Add calculated Net Power
    if "Net Power (MW)" in calculated.columns:
        telemetry_data["Net Power (MW)"] = calculated["Net Power (MW)"].tolist()

    # Add raw generation/consumption (try both mapped and original names)
    for orig_key, mapped_name in field_mapping.items():
        if orig_key in df.columns:
            orig_key_str = str(orig_key)
            mapped_name_str = str(mapped_name)
            if "Generation" in mapped_name_str or "Generation" in orig_key_str:
                telemetry_data[mapped_name] = df[orig_key].tolist()
                telemetry_data["RT_Generation_Qty"] = df[
                    orig_key
                ].tolist()  # Also include raw name
            elif "Consumption" in mapped_name_str or "Consumption" in orig_key_str:
                telemetry_data[mapped_name] = df[orig_key].tolist()
                telemetry_data["RT_Consumption_Qty"] = df[
                    orig_key
                ].tolist()  # Also include raw name

    # Market data - include both mapped and original names
    market_data = {}
    # Add calculated price spread
    if "RT - DA Price Spread ($/MWh)" in calculated.columns:
        market_data["RT - DA Price Spread ($/MWh)"] = calculated[
            "RT - DA Price Spread ($/MWh)"
        ].tolist()

    # Add RT SPP and DA SPP (try both mapped and original)
    for orig_key, mapped_name in field_mapping.items():
        if orig_key in df.columns:
            orig_key_str = str(orig_key)
            mapped_name_str = str(mapped_name)
            if (
                "RTSPP" in mapped_name_str
                or "RTSPP" in orig_key_str
                or "RT SPP" in mapped_name_str
            ):
                market_data[mapped_name] = df[orig_key].tolist()
                market_data["RTSPP_Avg"] = df[
                    orig_key
                ].tolist()  # Also include standard name
            elif (
                "DASPP" in mapped_name_str
                or "DASPP" in orig_key_str
                or "DA SPP" in mapped_name_str
            ):
                market_data[mapped_name] = df[orig_key].tolist()
                market_data["DASPP"] = df[
                    orig_key
                ].tolist()  # Also include standard name

    # Financial data - include both mapped and original names
    finance_data = {}
    # Add calculated Net Profit
    if "Net Profit ($)" in calculated.columns:
        finance_data["Net Profit ($)"] = calculated["Net Profit ($)"].tolist()

    # Add financial fields (try both mapped and original)
    for orig_key, mapped_name in field_mapping.items():
        if orig_key in df.columns:
            orig_key_str = str(orig_key)
            mapped_name_str = str(mapped_name)
            if "Energy_Amt" in orig_key_str or "Energy Amt" in mapped_name_str:
                finance_data[mapped_name] = df[orig_key].tolist()
                # Also include with standard naming
                if "RT_Energy_Amt" in orig_key_str:
                    finance_data["RT_Energy_Amt"] = df[orig_key].tolist()
                    finance_data["RT Energy Amt"] = df[orig_key].tolist()
                elif "DA_Energy_Amt" in orig_key_str:
                    finance_data["DA_Energy_Amt"] = df[orig_key].tolist()
                    finance_data["DA Energy Amt"] = df[orig_key].tolist()
            elif "BP_Dev" in orig_key_str or "BP Dev" in mapped_name_str:
                finance_data[mapped_name] = df[orig_key].tolist()
                finance_data["BP_Dev_Amt"] = df[orig_key].tolist()
                finance_data["BP Dev Amt"] = df[orig_key].tolist()
            elif (
                "Ancillary_Imbalance" in orig_key_str
                or "Ancillary Imbalance" in mapped_name_str
            ):
                finance_data[mapped_name] = df[orig_key].tolist()
                finance_data["RT_Ancillary_Imbalance_Amt"] = df[orig_key].tolist()

    # Ancillary Services (awards/reservations)
    awards_data = {}
    as_fields = [
        name.get("Gen_Reg_Up_Qty", "Gen_Reg_Up_Qty"),
        name.get("Gen_Reg_Down_Qty", "Gen_Reg_Down_Qty"),
        name.get("Gen_NS_Qty", "Gen_NS_Qty"),
        name.get("Gen_ECRS_Qty", "Gen_ECRS_Qty"),
        name.get("Gen_RRS_Qty", "Gen_RRS_Qty"),
    ]
    for field in as_fields:
        if field in df_renamed.columns:
            awards_data[field] = df_renamed[field].tolist()

    # Convert calculated metrics to lists
    calculated_data = {}
    for col in calculated.columns:
        calculated_data[col] = [
            None if pd.isna(value) else value for value in calculated[col].tolist()
        ]

    # Return structured response
    return {
        "telemetry": telemetry_data,
        "market": market_data,
        "awards": awards_data,
        "finance": finance_data,
        "calculated": calculated_data,
        "intervals": intervals,
        "identifier": qse_integration.qse_project_identifier,
        "all_data": {col: df_renamed[col].tolist() for col in df_renamed.columns},
        "units": unit_mapping,
        "available_columns": df_renamed.columns.tolist(),
    }


@router.get("/realtime/price")
async def get_realtime_price(
    user: Annotated[UserAuthed, Depends(get_user)],
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get the latest real-time settlement point price (RTSPP) for the project.

    Args:
        user: User authenticated by dependency injection.
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        db_async: Database session.

    Returns:
        Latest RTSPP value in $/MWh, or None if not available.
    """
    # Get QSE integration
    qse_integration_query = (
        core.crud.operational.qse_integrations.get_qse_integration_by_project_id(
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
        core.crud.operational.qse_integrations.get_qse_permissions_by_company_id(
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
        raise HTTPException(status_code=403, detail="Forbidden")

    # Get token
    token = await tps_token.get_token()

    ids = _get_ptp_identifiers(qse_integration=qse_integration)
    settlement_point_id = ids["settlement_point_id"]

    # Get current time range (last 1 hour to get latest price)
    tz = project.time_zone
    end = pd.Timestamp.now(tz=tz)
    start = end - pd.Timedelta(hours=1)

    # Convert to UTC
    begin_utc = start.tz_convert("UTC")
    end_utc = end.tz_convert("UTC")

    try:
        data = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint="Market-Prices",
            elements=[settlement_point_id],
            begin=begin_utc.isoformat().replace("+00:00", "Z"),
            end=end_utc.isoformat().replace("+00:00", "Z"),
        )

        # Find RTSPP data point and get the latest value
        rt_price = None
        latest_timestamp = None

        # Look for settlement point element with RTSPP data
        # First try to find by identifier match
        settlement_point_element = None
        for entry in data.get("data", []):
            if entry.get("identifier") == settlement_point_id:
                settlement_point_element = entry
                break

        # If not found by identifier, look for any settlement point with RTSPP data
        if not settlement_point_element:
            for entry in data.get("data", []):
                if entry.get("definition") == "Settlement Point" and any(
                    dp.get("keyName") == "RTSPP" for dp in entry.get("dataPoints", [])
                ):
                    settlement_point_element = entry
                    break

        if settlement_point_element:
            for dp in settlement_point_element.get("dataPoints", []):
                if dp.get("keyName") == "RTSPP":
                    values = dp.get("values", [])
                    if values:
                        # Get the most recent value (last in list, assuming sorted)
                        latest_value = values[-1]
                        if latest_value.get("data") and len(latest_value["data"]) > 0:
                            rt_price = float(latest_value["data"][0].get("value"))
                            latest_timestamp = latest_value.get("intervalStartUtc")
                            break

        return {
            "price": rt_price,
            "timestamp": latest_timestamp,
            "unit": "$/MWh",
            "settlement_point": project.interconnecting_substation,
            "qse_provider_name": (
                qse_integration.qse_provider.name_long
                if qse_integration.qse_provider
                else None
            ),
            "node_name": project.interconnecting_substation,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch real-time price: {exc}",
        ) from exc


@router.get("/identifiers")
async def get_project_identifiers(
    user: Annotated[UserAuthed, Depends(get_user)],
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get all PTP identifiers (parent and children) for the project.

    Queries multiple endpoints to find all identifiers related to the
    project's QSE identifier, including child identifiers that may be
    needed for different endpoints.

    Args:
        user: User authenticated by dependency injection.
        project: Project model provided by dependency injection.
        tps_token: Token manager for PTP API authentication.
        db_async: Database session.

    Returns:
        List of identifiers with metadata (identifier, element, definition,
        resource_id, parent_identifier).
    """
    # Get QSE integration
    qse_integration_query = (
        core.crud.operational.qse_integrations.get_qse_integration_by_project_id(
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
        core.crud.operational.qse_integrations.get_qse_permissions_by_company_id(
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
        raise HTTPException(status_code=403, detail="Forbidden")

    # Get token
    token = await tps_token.get_token()

    # Get parent identifier
    parent_identifier = qse_integration.qse_project_identifier

    # Optimized endpoint selection to minimize API calls.
    # Only query endpoints that return identifiers with direct parent-child
    # relationships to the entity ID (from qse_integrations table). This ensures
    # we only return identifiers that "fall under" the entity ID.
    #
    # Endpoints queried:
    # 1. Generator-Performance: Generators (more comprehensive than
    #    Real-Time-Unit-Position)
    # 2. Settlement-Charges: Entity identifiers (child entities)
    # 3. Real-Time-Unit-Position: Additional generator identifiers (if needed)
    # 4. Configuration-Awards: Resource_ID identifiers (Generator Config)
    #
    # Note: Market-Prices is NOT queried because it returns ALL settlement
    # points (1140+) regardless of parent relationship. Settlement points don't
    # have direct parent-child relationships with entities.

    # Use a recent date range to get current identifiers
    now = datetime.datetime.now(datetime.UTC)
    begin = (now - datetime.timedelta(days=7)).isoformat().replace("+00:00", "Z")
    end = (now + datetime.timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    # Note: Market-Prices is NOT queried here because it returns ALL settlement points
    # (1140+ entries) regardless of parent relationship. Settlement points don't have
    # a direct parent-child relationship with entities. If needed, settlement points
    # should be found through other means (e.g., project configuration).

    # 1 & 2: Query the two primary identifier sources concurrently.
    gen_perf_result, settlement_charges_result = await asyncio.gather(
        _safe_fetch_ptp_endpoint_data(
            token=token,
            endpoint="Generator-Performance",
            parent_identifier=parent_identifier,
            begin=begin,
            end=end,
        ),
        _safe_fetch_ptp_endpoint_data(
            token=token,
            endpoint="Settlement-Charges",
            parent_identifier=parent_identifier,
            begin=begin,
            end=end,
        ),
    )

    all_entries: list[dict[str, Any]] = []
    gen_perf_entries = (
        gen_perf_result.get("data", []) if isinstance(gen_perf_result, dict) else []
    )
    settlement_entries = (
        settlement_charges_result.get("data", [])
        if isinstance(settlement_charges_result, dict)
        else []
    )
    if isinstance(gen_perf_entries, list):
        all_entries.extend([e for e in gen_perf_entries if isinstance(e, dict)])
    if isinstance(settlement_entries, list):
        all_entries.extend([e for e in settlement_entries if isinstance(e, dict)])

    found_generator = any(e.get("definition") == "Generator" for e in all_entries)

    # 3. Real-Time-Unit-Position: Only if Generator-Performance did not yield
    # any Generator identifiers.
    if not found_generator:
        rtu_result = await _safe_fetch_ptp_endpoint_data(
            token=token,
            endpoint="Real-Time-Unit-Position",
            parent_identifier=parent_identifier,
            begin=begin,
            end=end,
        )
        rtu_entries = rtu_result.get("data", []) if isinstance(rtu_result, dict) else []
        if isinstance(rtu_entries, list):
            all_entries.extend([e for e in rtu_entries if isinstance(e, dict)])

    # 4. Configuration-Awards: expensive; only query if we still appear to be
    # missing (a) Resource_ID visibility and/or (b) Generator Configuration
    # identifiers.
    should_fetch_config_awards = not (
        _entries_have_resource_id(entries=all_entries)
        and _entries_have_generator_configuration(entries=all_entries)
    )
    if should_fetch_config_awards:
        config_awards_result = await _safe_fetch_ptp_endpoint_data(
            token=token,
            endpoint="Configuration-Awards",
            parent_identifier=parent_identifier,
            begin=begin,
            end=end,
        )
        config_entries = (
            config_awards_result.get("data", [])
            if isinstance(config_awards_result, dict)
            else []
        )
        if isinstance(config_entries, list):
            all_entries.extend([e for e in config_entries if isinstance(e, dict)])

    # Start with parent identifier
    related_identifiers = [
        {
            "identifier": parent_identifier,
            "element": "Parent QSE Identifier",
            "definition": "Primary QSE project identifier",
            "resource_id": None,
            "parent_identifier": None,
            "is_parent": True,
        }
    ]

    seen_identifiers = {parent_identifier}

    # Extract Resource_ID from parent identifier first (if available)
    parent_resource_id = None
    for entry in all_entries:
        if entry.get("identifier") == parent_identifier:
            parent_resource_id = _extract_resource_id(entry=entry)
            if parent_resource_id:
                related_identifiers[0]["resource_id"] = parent_resource_id
                break

    # Process entries from data queries
    for entry in all_entries:
        entry_id = entry.get("identifier")
        if not entry_id or entry_id in seen_identifiers:
            continue

        seen_identifiers.add(entry_id)

        element_name = entry.get("element", "")
        definition = entry.get("definition", "")
        parent_id = entry.get("parentIdentifier") or entry.get("parent")
        resource_id = None

        # Extract Resource_ID if available
        data_points = entry.get("dataPoints", [])
        for dp in data_points:
            if dp.get("keyName") == "Resource_ID":
                values = dp.get("values", [])
                for val in values:
                    if isinstance(val, dict):
                        value_data = val.get("data", [])
                        if value_data and len(value_data) > 0:
                            resource_id = str(value_data[0].get("value", ""))
                            break
                break

        is_parent = entry_id == parent_identifier
        is_child = parent_id == parent_identifier

        # Only include identifiers that have a direct relationship with the
        # parent entity:
        # 1. Is the parent identifier itself
        # 2. Has the parent as its parent (direct child relationship)
        # This ensures we only return identifiers that "fall under" the entity ID
        should_include = is_parent or is_child

        if should_include:
            # Update existing or add new
            existing_idx = next(
                (
                    idx
                    for idx, ident in enumerate(related_identifiers)
                    if ident["identifier"] == entry_id
                ),
                None,
            )

            if existing_idx is not None:
                # Update with Resource_ID if we found it
                if resource_id:
                    related_identifiers[existing_idx]["resource_id"] = resource_id
            else:
                related_identifiers.append(
                    {
                        "identifier": entry_id,
                        "element": element_name,
                        "definition": definition,
                        "resource_id": resource_id,
                        "parent_identifier": parent_id,
                        "is_parent": is_parent,
                    }
                )

    # Find MarketParticipant identifier by querying Customer_Position endpoint
    # The MarketParticipant is the top-level parent identifier shared by all
    # entities with the same Customer (QSE name)
    market_participant_identifier = None
    try:
        # Query Customer_Position without filter to get all entries
        all_customer_positions = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint="Customer_Position",
            elements=None,  # Get all
            begin=begin,
            end=end,
        )

        # Find the parent identifier entry and extract Customer name
        customer_name = None
        parent_entry = None
        for entry in all_customer_positions.get("data", []):
            if entry.get("identifier") == parent_identifier:
                parent_entry = entry
                data_points = entry.get("dataPoints", [])
                for dp in data_points:
                    if dp.get("keyName") == "Customer":
                        values = dp.get("values", [])
                        for val in values:
                            if isinstance(val, dict):
                                data_list = val.get("data", [])
                                for data_item in data_list:
                                    if isinstance(data_item, dict):
                                        customer_name = data_item.get("value")
                                        break
                                if customer_name:
                                    break
                        if customer_name:
                            break
                break

        # If we found a customer name, find all entities with that customer
        # and identify the top-level MarketParticipant identifier
        if customer_name:
            # Find all entities with the same Customer value
            entities_with_customer = []
            for entry in all_customer_positions.get("data", []):
                entry_customer = None
                data_points = entry.get("dataPoints", [])
                for dp in data_points:
                    if dp.get("keyName") == "Customer":
                        values = dp.get("values", [])
                        for val in values:
                            if isinstance(val, dict):
                                data_list = val.get("data", [])
                                for data_item in data_list:
                                    if isinstance(data_item, dict):
                                        entry_customer = data_item.get("value")
                                        break
                                if entry_customer:
                                    break
                        if entry_customer:
                            break

                if entry_customer == customer_name:
                    entities_with_customer.append(
                        {
                            "identifier": entry.get("identifier"),
                            "parent_identifier": entry.get("parentIdentifier"),
                        }
                    )

            # Find the top-level parent identifier (MarketParticipant)
            # This is the identifier that appears as a parent but not as a child
            all_parent_ids = {
                e["parent_identifier"]
                for e in entities_with_customer
                if e["parent_identifier"]
            }
            all_identifiers = {e["identifier"] for e in entities_with_customer}

            # The MarketParticipant is a parent ID that is not itself a child
            market_participant_candidates = [
                pid for pid in all_parent_ids if pid not in all_identifiers
            ]

            # If we found candidates, use the one that's highest in the hierarchy
            # (is the parent of our parent_identifier, or the most common parent)
            if market_participant_candidates:
                # Check if our parent_identifier's parent is in the candidates
                if parent_entry and parent_entry.get("parentIdentifier"):
                    parent_parent = parent_entry.get("parentIdentifier")
                    if parent_parent in market_participant_candidates:
                        market_participant_identifier = parent_parent
                    else:
                        # Use the first candidate (should be consistent)
                        market_participant_identifier = market_participant_candidates[0]
                else:
                    market_participant_identifier = market_participant_candidates[0]

    except Exception:
        logger.debug("Failed to find MarketParticipant identifier", exc_info=True)

    return {
        "identifiers": related_identifiers,
        "parent_identifier": parent_identifier,
        "market_participant_identifier": market_participant_identifier,
    }
