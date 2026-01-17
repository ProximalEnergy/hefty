from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
import requests
from app import dependencies, utils
from app.integrations.token_manager import TokenManager
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import core
from core import models

router = APIRouter(
    prefix="/battery-settlement",
    tags=["battery-settlement"],
    include_in_schema=utils.get_include_in_schema(),
)


def get_battery_settlement_details_dataframe(
    *,
    identifier: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    project: models.Project,
    token: str,
) -> pd.DataFrame:
    """todo

    Args:
        identifier: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        token: TODO: describe.
    """
    url = (
        "https://api.ptp.energy/v1/markets/ERCOTNodal/endpoints/"
        "Battery-Settlement-Details/data"
    )
    headers = {"Authorization": f"Bearer {token}"}
    tz = project.time_zone
    start_ts = start if start.tzinfo else start.tz_localize(tz)
    end_ts = end if end.tzinfo else end.tz_localize(tz)
    begin_utc = start_ts.tz_convert("UTC")
    end_utc = end_ts.tz_convert("UTC")
    params = {
        "begin": begin_utc.isoformat().replace("+00:00", "Z"),
        "end": end_utc.isoformat().replace("+00:00", "Z"),
        "elements": [identifier],
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch settlement data: {exc}",
        ) from exc

    payload = response.json()
    data = next(
        (
            entry
            for entry in payload.get("data", [])
            if entry.get("identifier") == identifier
        ),
        None,
    )
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Identifier {identifier} not found in settlement data",
        )

    df = pd.DataFrame()

    for dp in data["dataPoints"]:
        temp = pd.DataFrame(dp["values"])
        temp["intervalStartUtc"] = pd.to_datetime(temp["intervalStartUtc"])
        temp["intervalEndUtc"] = pd.to_datetime(temp["intervalEndUtc"])
        temp["data"] = temp["data"].apply(lambda x: float(x[0]["value"]))
        temp = temp.set_index("intervalStartUtc")
        temp = temp.rename(columns={"data": dp["keyName"]}).drop(
            columns=["intervalEndUtc"]
        )
        df = pd.concat([df, temp], axis=1)
    df.index = df.index.tz_convert(project.time_zone)  # type: ignore
    df.index.name = "time"

    return df


@router.get("")
async def get_battery_settlement_details(
    start: datetime.datetime,
    end: datetime.datetime,
    project: models.Project = Depends(dependencies.get_project_api),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    user: models.User = Depends(dependencies.get_user_data_async),
    db_async: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        tps_token: TODO: describe.
        user: TODO: describe.
        db_async: TODO: describe.
    """
    qse_integration = (
        await core.crud.operational.qse_integrations.get_qse_integration_by_project_id(
            db=db_async,
            project_id=project.project_id,
        )
    )
    if qse_integration is None:
        raise HTTPException(status_code=404, detail="QSE integration not found")

    permissions_query = (
        core.crud.operational.qse_integrations.get_qse_permissions_by_company_id(
            company_id=user.company_id,
        )
    )
    permissions = await permissions_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    has_permission = any(
        perm.qse_integration_id == qse_integration.qse_integration_id and perm.can_view
        for perm in permissions
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="Forbidden")
    fields = await core.crud.operational.qse_integrations.get_qse_fields_by_provider_id(
        db=db_async, provider_id=qse_integration.qse_provider_id
    )
    fields_df = core.utils.core_utils.model_list_to_pandas(model_list=fields).set_index(
        "qse_field_name"
    )
    token = await tps_token.get_token()
    df = get_battery_settlement_details_dataframe(
        identifier=qse_integration.qse_project_identifier,
        start=pd.to_datetime(start).tz_convert(project.time_zone),
        end=pd.to_datetime(end).tz_convert(project.time_zone),
        project=project,
        token=token,
    )
    # Replace NaN values with None for JSON serialization
    df = df.replace(np.nan, None)
    df = df.rename(columns=fields_df["name_long"].to_dict())
    qse_data = {
        "index": df.index.tolist(),
        "unit": fields_df.set_index("name_long")["unit"].to_dict(),
        "data": {x: y for x, y in zip(df.columns.tolist(), df.T.values.tolist())},
    }

    name = fields_df["name_long"].to_dict()

    # Long names used below (match renamed df columns)
    RT_GEN = name.get("RT_Generation_Qty", "RT_Generation_Qty")
    RT_CON = name.get("RT_Consumption_Qty", "RT_Consumption_Qty")
    RT_SPP = name.get("RTSPP_Avg", "RTSPP_Avg")
    DA_SPP = name.get("DASPP", "DASPP")
    DA_SALES = name.get("DA_Sales_Qty", "DA_Sales_Qty")
    DA_PURCH = name.get("DA_Purchases_Qty", "DA_Purchases_Qty")
    RT_EN_AMT = name.get("RT_Energy_Amt", "RT_Energy_Amt")
    DA_EN_AMT = name.get("DA_Energy_Amt", "DA_Energy_Amt")
    BP_DEV = name.get("BP_Dev_Amt", "BP_Dev_Amt")
    RT_AS_IMB = name.get("RT_Ancillary_Imbalance_Amt", "RT_Ancillary_Imbalance_Amt")
    RT_REL_IMB = name.get(
        "RT_Reliability_Deployment_Imbalance_Amt",
        "RT_Reliability_Deployment_Imbalance_Amt",
    )

    # Make a zero-aligned Series helper
    def zero_series() -> pd.Series[float]:
        """todo"""
        return pd.Series(0.0, index=df.index, dtype="float64")

    # Safely fetch a numeric Series by column name, or a zero series if missing
    def s(col_name: str) -> pd.Series:  # nosemgrep: python-enforce-keyword-only-args
        """todo

        Args:
            col_name: TODO: describe.
        """
        if col_name in df.columns:
            return pd.to_numeric(df[col_name], errors="coerce")
        return zero_series()

    # ---------- Derived metrics ----------
    out = pd.DataFrame(index=df.index)

    # Net positions & deviation
    if (RT_GEN in df.columns) or (RT_CON in df.columns):
        out["Net Position"] = s(RT_GEN) - s(RT_CON)

    if (DA_SALES in df.columns) or (DA_PURCH in df.columns):
        out["DA Net Position"] = s(DA_SALES) - s(DA_PURCH)

    if ("Net Position" in out.columns) and ("DA Net Position" in out.columns):
        out["DA vs RT Deviation"] = out["Net Position"] - out["DA Net Position"]

    # Price spread
    if (RT_SPP in df.columns) and (DA_SPP in df.columns):
        out["RT - DA Price Spread"] = s(RT_SPP) - s(DA_SPP)

    # Throughput
    if (RT_GEN in df.columns) or (RT_CON in df.columns):
        out["Throughput"] = s(RT_GEN) + s(RT_CON)

    # Energy revenues: prefer settlement amounts; fallback to qty×price
    # RT
    if RT_EN_AMT in df.columns:
        out["RT Energy Revenue"] = s(RT_EN_AMT)
    elif (RT_SPP in df.columns) and ("Net Position" in out.columns):
        out["RT Energy Revenue"] = out["Net Position"] * s(RT_SPP)

    # DA
    if DA_EN_AMT in df.columns:
        out["DA Energy Revenue"] = s(DA_EN_AMT)
    elif (DA_SPP in df.columns) and ("DA Net Position" in out.columns):
        out["DA Energy Revenue"] = out["DA Net Position"] * s(DA_SPP)

    # Total energy revenue
    if ("RT Energy Revenue" in out.columns) or ("DA Energy Revenue" in out.columns):
        out["Total Energy Revenue"] = out.get(
            "RT Energy Revenue", zero_series()
        ).fillna(0.0) + out.get("DA Energy Revenue", zero_series()).fillna(0.0)

    # Imbalance totals
    if (
        (BP_DEV in df.columns)
        or (RT_AS_IMB in df.columns)
        or (RT_REL_IMB in df.columns)
    ):
        out["Total Imbalance Amount"] = s(BP_DEV) + s(RT_AS_IMB) + s(RT_REL_IMB)

    # Net Profit = energy revenue + imbalances (signs assumed native)
    if ("Total Energy Revenue" in out.columns) or (
        "Total Imbalance Amount" in out.columns
    ):
        out["Net Profit"] = out.get("Total Energy Revenue", zero_series()).fillna(
            0.0
        ) + out.get("Total Imbalance Amount", zero_series()).fillna(0.0)

    # Profit per Throughput
    if ("Net Profit" in out.columns) and ("Throughput" in out.columns):
        denom = out["Throughput"].replace({0.0: np.nan})
        out["Profit per Throughput"] = out["Net Profit"] / denom

    # Cumulative metrics
    for col in [
        "Net Profit",
        "Total Energy Revenue",
        "Total Imbalance Amount",
    ]:
        if col in out.columns:
            out[f"Cumulative {col}"] = out[col].fillna(0.0).cumsum()

    # Units for calculated series
    calculated_units = {
        "RT - DA Price Spread": "$/MWh",
        "Net Position": "MWh",
        "DA Net Position": "MWh",
        "DA vs RT Deviation": "MWh",
        "Throughput": "MWh",
        "RT Energy Revenue": "$",
        "DA Energy Revenue": "$",
        "Total Energy Revenue": "$",
        "Total Imbalance Amount": "$",
        "Net Profit": "$",
        "Profit per Throughput": "$/MWh",
        "Cumulative Net Profit": "$",
        "Cumulative Total Energy Revenue": "$",
        "Cumulative Total Imbalance Amount": "$",
    }

    # Keep only computed columns
    keep_cols = [c for c in calculated_units if c in out.columns]
    df_calc = out[keep_cols].copy()

    # JSON-friendly (None instead of NaN)
    df_calc = df_calc.replace({np.nan: None})
    calculated_units = {
        k: v for k, v in calculated_units.items() if k in df_calc.columns
    }

    calculated_data = {
        "index": df.index.tolist(),
        "unit": calculated_units,
        "data": {col: df_calc[col].tolist() for col in df_calc.columns},
    }

    return {
        "qse_data": qse_data,
        "calculated_data": calculated_data,
        "tsk_identifier": qse_integration.qse_project_identifier,
    }
