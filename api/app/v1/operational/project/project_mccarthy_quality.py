import os

import pandas as pd
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app import interfaces

router = APIRouter(prefix="/projects/{project_id}/quality")


@router.get("/inspections", response_model=list[interfaces.Inspection])
def get_inspections():
    # Get folder of current file
    """todo"""
    folder = os.path.dirname(os.path.abspath(__file__))

    df: pd.DataFrame = pd.read_pickle(f"{folder}/quality_data/quality_inspections.pkl")  # type: ignore
    df = df.astype({"id": int, "device_id": int})

    # Drop any rows that have a Nan value
    df = df.dropna()

    return df.to_dict("records")


@router.get(
    "/observations",
    response_model=list[interfaces.Observation],
    response_class=ORJSONResponse,
)
def get_observations():
    # Get folder of current file
    """todo"""
    folder = os.path.dirname(os.path.abspath(__file__))

    df: pd.DataFrame = pd.read_pickle(f"{folder}/quality_data/quality_observations.pkl")  # type: ignore
    df = df.astype({"id": int, "device_id": int})

    # Convert nan values in string column to none
    df["description"] = df["description"].apply(lambda x: None if pd.isna(x) else x)
    df["impact_level"] = df["impact_level"].apply(lambda x: None if pd.isna(x) else x)
    df["priority"] = df["priority"].apply(lambda x: None if pd.isna(x) else x)
    df["spec_section"] = df["spec_section"].apply(
        lambda x: None if pd.isna(x) else str(x),
    )
    df["trade_name"] = df["trade_name"].apply(lambda x: None if pd.isna(x) else x)
    df["inspection_origin"] = df["inspection_origin"].apply(
        lambda x: None if pd.isna(x) else x,
    )
    df["id"] = df["id"].astype(int)
    df["device_id"] = df["device_id"].astype(int)

    return df.to_dict("records")
