import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from pandas.tseries.offsets import DateOffset
from sqlalchemy.ext.asyncio import AsyncSession

from app import custom_types, dependencies, interfaces
from app._crud.ercot.dam_spp import get_ercot_dam_spp as crud_get_ercot_dam_spp
from app._crud.ercot.dmes import get_ercot_dmes as crud_get_ercot_dmes
from app._crud.ercot.qses import get_ercot_qses as crud_get_ercot_qses
from app._crud.ercot.resources import get_ercot_resource as crud_get_ercot_resource
from app._crud.ercot.resources import get_ercot_resources as crud_get_ercot_resources
from app._crud.ercot.rtm_spp import get_ercot_rtm_spp as crud_get_ercot_rtm_spp
from app._crud.ercot.sced_gen import get_ercot_sced_gen as crud_get_ercot_sced_gen
from app._crud.ercot.sced_load import get_ercot_sced_load as crud_get_ercot_sced_load
from app._crud.ercot.settlement_point_markets import (
    get_ercot_settlement_point_markets as crud_get_ercot_settlement_point_markets,
)
from app._crud.ercot.settlement_point_types import (
    get_ercot_settlement_point_types as crud_get_ercot_settlement_point_types,
)
from app._crud.ercot.settlement_points import (
    get_ercot_settlement_points as crud_get_ercot_settlement_points,
)

router = APIRouter(prefix="/ercot", tags=["ercot"])


@router.get(
    "/settlement_point_markets",
    response_model=list[interfaces.SettlementPointMarket],
)
async def get_settlement_point_markets(
    db: Annotated[AsyncSession, Depends(dependencies.get_ercot_db_async)],
):
    return await crud_get_ercot_settlement_point_markets(db=db)


@router.get(
    "/settlement_point_types",
    response_model=list[interfaces.SettlementPointType],
)
async def get_settlement_point_types(
    name_long: str = "",
    db: AsyncSession = Depends(dependencies.get_ercot_db_async),
):
    return await crud_get_ercot_settlement_point_types(db=db, name_long=name_long)


@router.get(
    "/settlement_points",
    response_model=list[interfaces.SettlementPoint],
)
async def get_settlement_points(
    deep: custom_types.AnnotatedDeep = False,
    db: AsyncSession = Depends(dependencies.get_ercot_db_async),
):
    return await crud_get_ercot_settlement_points(db=db, deep=deep)


@router.get(
    "/qses",
    response_model=list[interfaces.QSE],
)
async def get_qses(
    db: Annotated[AsyncSession, Depends(dependencies.get_ercot_db_async)],
):
    return await crud_get_ercot_qses(db=db)


@router.get(
    "/dmes",
    response_model=list[interfaces.DME],
)
async def get_dmes(
    db: Annotated[AsyncSession, Depends(dependencies.get_ercot_db_async)],
):
    return await crud_get_ercot_dmes(db=db)


@router.get(
    "/resources",
    response_model=list[interfaces.Resource],
)
async def get_resources(
    deep: custom_types.AnnotatedDeep = False,
    db: AsyncSession = Depends(dependencies.get_ercot_db_async),
):
    return await crud_get_ercot_resources(db=db, deep=deep)


@router.get(
    "/resources/{resource_id}",
    response_model=interfaces.Resource,
)
async def get_resource(
    resource_id: int,
    deep: custom_types.AnnotatedDeep = False,
    db: AsyncSession = Depends(dependencies.get_ercot_db_async),
):
    return await crud_get_ercot_resource(db=db, resource_id=resource_id, deep=deep)


@router.get(
    "/resources/{resource_id}/net-power",
)
async def get_resource_net_power(
    resource_id: int,
    db: Annotated[AsyncSession, Depends(dependencies.get_ercot_db_async)],
):
    start = pd.Timestamp.now(tz="US/Central").floor("D") - DateOffset(days=60)
    end = start + DateOffset(days=1)

    resource = await crud_get_ercot_resource(db=db, resource_id=resource_id)
    sced_gen_data = await crud_get_ercot_sced_gen(
        db,
        resource_id=resource_id,
        start=start,
        end=end,
    )
    sced_load_data = await crud_get_ercot_sced_load(
        db,
        resource_id=resource_id,
        start=start,
        end=end,
    )
    dam_spp_data = await crud_get_ercot_dam_spp(
        db,
        settlement_point_ids=[resource.settlement_point_id],
        start=start,
        end=end,
    )
    rtm_spp_data = await crud_get_ercot_rtm_spp(
        db=db,
        settlement_point_ids=[resource.settlement_point_id],
        start=start,
        end=end,
    )

    # Check if any data is missing
    if any(
        [
            len(d) == 0
            for d in [sced_gen_data, sced_load_data, dam_spp_data, rtm_spp_data]
        ],
    ):
        raise HTTPException(
            status_code=404,
            detail="Data not found",
        )

    df_gen = pd.DataFrame.from_records([d.__dict__ for d in sced_gen_data])
    df_gen = df_gen[["power_generated", "time"]].set_index("time").sort_index()

    df_load = pd.DataFrame.from_records([d.__dict__ for d in sced_load_data])
    df_load = df_load[["power_consumed", "time"]].set_index("time").sort_index()

    df_dam = pd.DataFrame.from_records([d.__dict__ for d in dam_spp_data])
    df_dam = df_dam.set_index("time")
    df_dam.index = df_dam.index.tz_convert("US/Central")  # type: ignore

    df_rtm = pd.DataFrame.from_records([d.__dict__ for d in rtm_spp_data])
    df_rtm = df_rtm.set_index("time")
    df_rtm.index = df_rtm.index.tz_convert("US/Central")  # type: ignore

    df = pd.concat([df_gen, df_load], axis=1)

    df["power_net"] = df["power_generated"] - df["power_consumed"]
    df.index = df.index.tz_convert("US/Central")  # type: ignore

    return [
        {
            "x": df.index.tolist(),
            "y": df["power_net"].tolist(),
            "y_range": [-resource.capacity_power, resource.capacity_power],
            "yaxis": "y",
            "name": "Net Power",
        },
        {
            "x": df_dam.index.tolist(),
            "y": df_dam["price"].tolist(),
            "yaxis": "y2",
            "name": "Day-Ahead SPP",
        },
        {
            "x": df_rtm.index.tolist(),
            "y": df_rtm["price"].tolist(),
            "yaxis": "y2",
            "name": "Real-Time SPP",
        },
    ]


@router.get("/prices")
async def get_prices(
    settlement_point_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
    db: Annotated[AsyncSession, Depends(dependencies.get_ercot_db_async)],
):
    dam_spp = await crud_get_ercot_dam_spp(
        db,
        settlement_point_ids=[settlement_point_id],
        start=start,
        end=end,
    )
    rtm_spp = await crud_get_ercot_rtm_spp(
        db,
        settlement_point_ids=[settlement_point_id],
        start=start,
        end=end,
    )

    if len(dam_spp) > 0:
        df_dam = pd.DataFrame.from_records([d.__dict__ for d in dam_spp])
        df_dam = df_dam.set_index("time")
        df_dam = df_dam.sort_index()
        df_dam.index = df_dam.index.tz_convert("US/Central")  # type: ignore
        dam_data = {
            "x": df_dam.index.tolist(),
            "y": df_dam["price"].tolist(),
            "name": "Day-Ahead SPP",
        }
    else:
        dam_data = {}

    if len(rtm_spp) > 0:
        df_rtm = pd.DataFrame.from_records([d.__dict__ for d in rtm_spp])
        df_rtm = df_rtm.set_index("time")
        df_rtm = df_rtm.sort_index()
        df_rtm.index = df_rtm.index.tz_convert("US/Central")  # type: ignore
        rtm_data = {
            "x": df_rtm.index.tolist(),
            "y": df_rtm["price"].tolist(),
            "name": "Real-Time SPP",
        }
    else:
        rtm_data = {}

    return [
        dam_data,
        rtm_data,
    ]
