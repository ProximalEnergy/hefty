import json
from collections.abc import Generator
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.logger import logger


def get_secret(
    *,
    secret_name: str,
    region_name: str | None = "us-east-2",
) -> dict[Any, Any]:
    """
    Get a secret from AWS Secrets Manager.
    Relies on AWS's native caching mechanism for optimal performance.

    Args:
        secret_name (str): The name of the secret to get.
        region_name (str): The region to use for the secret.

    Returns:
        Dict[Any, Any]: The secret value as a dictionary.
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        # Get the secret value - AWS handles caching automatically
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/
        # API_GetSecretValue.html
        raise e

    # Return the secret value
    result = json.loads(get_secret_value_response["SecretString"])
    return dict(result)


def _iterate_parameter_pages(
    *,
    client: Any,
    path: str,
    recursive: bool,
) -> Generator[dict[str, Any], None, None]:
    """Yield paginated SSM parameter responses.

    Args:
        client: Boto3 SSM client used for the request.
        path: Parameter path prefix to search under.
        recursive: Whether to include nested paths.
    """
    try:
        paginator = client.get_paginator("get_parameters_by_path")
        yield from paginator.paginate(
            Path=path,
            Recursive=recursive,
            WithDecryption=True,
        )
    except ClientError as e:
        logger.error(f"Error retrieving parameters from SSM: {e}")
        raise


def get_parameters_by_path(
    *,
    path: str,
    region_name: str | None = "us-east-2",
    recursive: bool = False,
) -> dict[str, str]:
    """Retrieve decrypted parameters stored under an SSM parameter path.

    Args:
        path: Parameter path prefix to search under.
        region_name: AWS region to use for the SSM client.
        recursive: Whether to include nested paths.
    """

    session = boto3.session.Session()
    client = session.client(service_name="ssm", region_name=region_name)

    parameters: dict[str, str] = {}
    for page in _iterate_parameter_pages(
        client=client,
        path=path,
        recursive=recursive,
    ):
        for parameter in page.get("Parameters", []):
            name = parameter["Name"].rsplit("/", maxsplit=1)[-1]
            parameters[name] = parameter["Value"]

    return parameters
