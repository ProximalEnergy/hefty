#!/usr/bin/env python3
"""Ensure local pv-eem version is higher than deployed Lambda version."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

SemVer = tuple[int, int, int]
_SEMVER_RE = re.compile(
    r"^v?(?P<major>\d+)(?:\.|-)(?P<minor>\d+)(?:\.|-)(?P<patch>\d+)$"
)
_DEFAULT_FUNCTION_NAME = "pv-eem"


def _is_resource_not_found_error(
    *,
    error: ClientError,
) -> bool:
    raw_error = error.response.get("Error")
    if not isinstance(raw_error, dict):
        return False

    error_code = raw_error.get("Code")
    return isinstance(error_code, str) and error_code == "ResourceNotFoundException"


@dataclass(frozen=True)
class ImageReference:
    """Container image reference parsed from Lambda function code URI."""

    registry: str
    repository: str
    tag: str | None
    digest: str | None


def _parse_semver(
    *,
    raw: str,
) -> SemVer | None:
    match = _SEMVER_RE.match(raw.strip())
    if match is None:
        return None

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def _format_semver(
    *,
    version: SemVer,
) -> str:
    major, minor, patch = version
    return f"{major}.{minor}.{patch}"


def _read_local_version(
    *,
    pyproject_path: Path,
) -> SemVer:
    with pyproject_path.open("rb") as file_handle:
        pyproject = tomllib.load(file_handle)

    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("Could not find [project] table in pyproject.toml.")

    raw_version = project.get("version")
    if not isinstance(raw_version, str):
        raise RuntimeError("Could not find project.version in pyproject.toml.")

    parsed = _parse_semver(raw=raw_version)
    if parsed is None:
        raise RuntimeError(
            "Local pyproject version is not a supported semver string: "
            f"{raw_version}"
        )
    return parsed


def _parse_image_reference(
    *,
    image_uri: str,
) -> ImageReference:
    if "/" not in image_uri:
        raise RuntimeError(f"Unexpected image URI format: {image_uri}")

    registry, repository_ref = image_uri.split("/", maxsplit=1)
    repository = repository_ref
    tag: str | None = None
    digest: str | None = None

    if "@" in repository_ref:
        repository, digest = repository_ref.split("@", maxsplit=1)
    elif ":" in repository_ref:
        repository, tag = repository_ref.rsplit(":", maxsplit=1)

    return ImageReference(
        registry=registry,
        repository=repository,
        tag=tag,
        digest=digest,
    )


def _extract_region_from_arn(
    *,
    function_arn: str,
) -> str:
    arn_parts = function_arn.split(":")
    if len(arn_parts) < 4 or not arn_parts[3]:
        raise RuntimeError(f"Could not parse region from Lambda ARN: {function_arn}")
    return arn_parts[3]


def _extract_registry_id(
    *,
    registry: str,
) -> str | None:
    prefix = registry.split(".", maxsplit=1)[0]
    return prefix if prefix.isdigit() else None


def _get_lambda_function_data(
    *,
    function_name: str,
) -> tuple[str, str] | None:
    lambda_client = boto3.client("lambda")
    try:
        response = lambda_client.get_function(FunctionName=function_name)
    except ClientError as exc:
        if _is_resource_not_found_error(error=exc):
            return None
        raise

    code = response.get("Code")
    config = response.get("Configuration")
    if not isinstance(code, dict) or not isinstance(config, dict):
        raise RuntimeError("Unexpected Lambda get_function response format.")

    image_uri = code.get("ImageUri")
    function_arn = config.get("FunctionArn")
    if not isinstance(image_uri, str) or not image_uri:
        raise RuntimeError(
            "Lambda function does not contain a container image URI."
        )
    if not isinstance(function_arn, str) or not function_arn:
        raise RuntimeError("Lambda function response is missing FunctionArn.")

    return image_uri, function_arn


def _resolve_tags_for_digest(
    *,
    image_ref: ImageReference,
    region: str,
) -> list[str]:
    if image_ref.digest is None:
        return []

    ecr_client = boto3.client("ecr", region_name=region)
    request: dict[str, Any] = {
        "repositoryName": image_ref.repository,
        "imageIds": [{"imageDigest": image_ref.digest}],
    }
    registry_id = _extract_registry_id(registry=image_ref.registry)
    if registry_id is not None:
        request["registryId"] = registry_id

    response = ecr_client.describe_images(**request)
    details = response.get("imageDetails")
    if not isinstance(details, list) or not details:
        raise RuntimeError(
            "Could not resolve deployed image digest to ECR image details."
        )

    tags: list[str] = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        detail_tags = detail.get("imageTags")
        if not isinstance(detail_tags, list):
            continue
        for detail_tag in detail_tags:
            if isinstance(detail_tag, str):
                tags.append(detail_tag)
    return tags


def _resolve_deployed_version(
    *,
    function_name: str,
) -> tuple[SemVer, list[str]] | None:
    lambda_data = _get_lambda_function_data(function_name=function_name)
    if lambda_data is None:
        return None

    image_uri, function_arn = lambda_data
    image_ref = _parse_image_reference(image_uri=image_uri)

    observed_tags: list[str] = []
    if image_ref.tag is not None:
        observed_tags.append(image_ref.tag)

    region = _extract_region_from_arn(function_arn=function_arn)
    observed_tags.extend(_resolve_tags_for_digest(image_ref=image_ref, region=region))

    unique_tags = sorted(set(observed_tags))
    semvers: list[SemVer] = []
    for tag in unique_tags:
        parsed = _parse_semver(raw=tag)
        if parsed is not None:
            semvers.append(parsed)

    if not semvers:
        tag_summary = ", ".join(unique_tags) if unique_tags else "<none>"
        raise RuntimeError(
            "No semver-like deployed image tags found for Lambda. "
            f"Observed tags: {tag_summary}"
        )

    return max(semvers), unique_tags


def main_check_deployed_version() -> int:
    function_name = _DEFAULT_FUNCTION_NAME

    try:
        local_version = _read_local_version(pyproject_path=Path("pyproject.toml"))
        deployed_version_data = _resolve_deployed_version(
            function_name=function_name,
        )
    except (BotoCoreError, ClientError, RuntimeError, OSError) as exc:
        print(f"Version gate failed: {exc}")
        return 1

    print(f"Lambda function: {function_name}")
    print(f"Local version: {_format_semver(version=local_version)}")
    if deployed_version_data is None:
        print("No deployed Lambda function found in active AWS account/region.")
        print("Version gate passed (first deploy).")
        return 0

    deployed_version, observed_tags = deployed_version_data
    print(f"Deployed version: {_format_semver(version=deployed_version)}")
    if observed_tags:
        print(f"Observed deployed tags: {', '.join(observed_tags)}")

    if local_version <= deployed_version:
        print("Local version must be higher than the deployed Lambda version.")
        return 1

    print("Version gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_check_deployed_version())
