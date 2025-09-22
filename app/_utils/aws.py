import json
from typing import Any

import boto3
from botocore.exceptions import ClientError


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
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Return the secret value
    return json.loads(get_secret_value_response["SecretString"])
