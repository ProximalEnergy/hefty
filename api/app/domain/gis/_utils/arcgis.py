"""
Error codes:
    - 498:  Token expired
    - 499:  Token expired
"""

import json
from typing import TYPE_CHECKING

import requests

from app._utils.aws import get_secret

if TYPE_CHECKING:
    from app.domain.gis.map import ArcGISProvider


def get_arcgis_token(
    *,
    provider: "ArcGISProvider",
) -> str:
    # --- Get secret from AWS Secrets Manager ---
    """todo

    Args:
        provider: TODO: describe.
    """
    secret_name = "map_integrations/arcgis/1"  # noqa: S105
    REGION_NAME = "us-east-2"
    secret = get_secret(
        secret_name=secret_name,
        region_name=REGION_NAME,
    )

    # --- Get information from provider ---
    arcgis_token_url = provider.arcgis_token_url
    if not arcgis_token_url:
        raise ValueError("ArcGIS token URL is not provided")

    # --- Request ---
    params = {
        "username": secret["username"],
        "password": secret["password"],
        "client": "requestip",
        "expiration": 60,  # 5 minutes
        "f": "json",
    }

    response = requests.post(arcgis_token_url, data=params)

    # --- Success Path ---
    if response.status_code == 200:
        token_info = json.loads(response.text)
        if "token" in token_info:
            return str(token_info["token"])

        # --- Failure Path ---
        else:
            raise ValueError(f"Token not found in response: {token_info}")
    else:
        raise ValueError(f"Request failed with status code: {response.status_code}")
