"""Load Lambda configuration from env or AWS Secrets Manager."""

import json
import os

import boto3
from botocore.exceptions import ClientError

_DEFAULT_SECRET_NAME = "microservices/jigsaw_analysis"  # noqa: S105


def load_jigsaw_analysis_config_into_env() -> None:
    """Merge secrets into os.environ when a secret name is configured.

    When ``JIGSAW_ANALYSIS_SECRET_NAME`` is unset, existing Lambda env vars are
    used (supports legacy ``jigsaw-analysis-docker`` configuration).
    """
    secret_name = os.getenv("JIGSAW_ANALYSIS_SECRET_NAME", _DEFAULT_SECRET_NAME)
    if os.getenv("JIGSAW_ANALYSIS_SKIP_SECRETS") == "1":
        return

    region = os.getenv("AWS_REGION", "us-east-2")
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise
        required = ("PROXIMAL_API_KEY", "CONNECTION_STRING")
        if all(os.getenv(key) for key in required):
            return
        msg = f"Secret {secret_name} not found and required env vars are missing"
        raise ValueError(msg) from exc

    secret_string = response.get("SecretString")
    if not secret_string:
        msg = f"Secret {secret_name} has no SecretString"
        raise ValueError(msg)

    for key, value in json.loads(secret_string).items():
        os.environ[key] = str(value)
