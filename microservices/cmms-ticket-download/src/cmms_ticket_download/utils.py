import json
from typing import Any, cast

import boto3
from botocore.exceptions import ClientError


def ensure_200(*, response: Any, detail: Any = None) -> None:
    """Raise Exception if response status code is not 200.
    This function works with httpx Response objects.

    Args:
        response (Any): Response object to check (httpx.Response).
        detail (Any, optional): Error detail message. Defaults to None.

    Raises:
        Exception: If response status code is not 200.
    """
    if not hasattr(response, "status_code"):
        raise Exception("Response object has no status_code attribute")

    if response.status_code != 200:
        error_msg = detail or f"Request failed with status code {response.status_code}"
        if hasattr(response, "text"):
            error_msg += f": {response.text}"
        raise Exception(error_msg)


def get_cmms_ticket_download_secret(
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
    return cast(dict[Any, Any], json.loads(get_secret_value_response["SecretString"]))
