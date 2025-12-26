import datetime
import json
import logging
from typing import Annotated

import boto3
from app import dependencies, utils
from app.logger import logger
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException, Query

from core import models

router = APIRouter(
    prefix="/combiner-correlation-analysis",
    tags=["combiner-correlation-analysis"],
    dependencies=[Depends(dependencies.check_project_access_async)],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get("")
async def combiner_correlation_analysis(
    *,
    analysis_date: datetime.datetime | None = None,
    block_names: Annotated[list[str] | None, Query()] = None,
    project: models.Project = Depends(dependencies.get_project_api),
):
    """todo

    Args:
        analysis_date: TODO: describe.
        block_names: TODO: describe.
        project: TODO: describe.
    """

    lambda_client = boto3.client(
        "lambda",
        region_name="us-east-2",
        config=Config(
            connect_timeout=10,
            read_timeout=900,
            retries={"max_attempts": 3},
        ),
    )

    payload = {
        "project_id": str(project.project_id),
        "analysis_date": analysis_date.strftime("%Y-%m-%d") if analysis_date else None,
        "block_names": block_names,
    }

    try:
        response = lambda_client.invoke(
            FunctionName="jigsaw-analysis-docker",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        response_payload = json.loads(response["Payload"].read())
        results = json.loads(response_payload["body"])
        logging.info(results)
        return results
    except Exception as exc:
        logger.error("Error invoking Lambda function: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing analysis request: {exc}",
        ) from exc
