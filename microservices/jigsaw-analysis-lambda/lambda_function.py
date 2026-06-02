import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

SENTRY_DSN = (
    "https://11a4bd8327572edf71196106139c0298"
    "@o4506555874672640.ingest.us.sentry.io/4510524365799424"
)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

import json  # noqa: E402
from typing import Any  # noqa: E402

from config import load_jigsaw_analysis_config_into_env  # noqa: E402
from jigsaw import analyze_project_combiners  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

load_jigsaw_analysis_config_into_env()


class JigsawAnalysisEvent(BaseModel):
    """Lambda payload for combiner correlation analysis."""

    project_id: str
    analysis_date: str | None = None
    block_names: list[str] | None = Field(default=None)


def lambda_handler(
    event: dict[str, Any],
    _context: Any,  # noqa: ANN401, ARG001
) -> dict[str, Any]:
    """Run combiner mismatch detection for one or more blocks.

    Args:
        event: ``project_id``, ``analysis_date``, optional ``block_names``.
        _context: AWS Lambda context (unused).

    Returns:
        API Gateway style dict with JSON body of swap recommendations.
    """
    try:
        payload = JigsawAnalysisEvent.model_validate(event)
    except Exception as exc:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(exc)}),
        }

    try:
        results = analyze_project_combiners(
            project_id=payload.project_id,
            analysis_date=payload.analysis_date,
            block_names=payload.block_names,
        )
        return {
            "statusCode": 200,
            "body": json.dumps(results),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)}),
        }
