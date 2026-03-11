#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MONO_ROOT="$(cd "${PROJECT_ROOT}/.." && pwd)"
PYPROJECT_PATH="${PROJECT_ROOT}/pyproject.toml"
ECR_REPOSITORY="${PVEEM_ECR_REPOSITORY:-pv-expected-energy/simulation}"

version_tag="$(
  grep '^version = "' "${PYPROJECT_PATH}" |
    head -n 1 |
    sed 's/version = "\(.*\)"/\1/'
)"

if [[ -z "${version_tag}" ]]; then
  echo "[push-image] Could not read version from pyproject.toml."
  exit 1
fi

. "${MONO_ROOT}/_scripts/auth_aws_codeartifact.sh"

aws_region="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
if [[ -z "${aws_region}" ]]; then
  aws_region="$(aws configure get region 2>/dev/null || true)"
fi

if [[ -z "${aws_region}" ]]; then
  echo "[push-image] AWS region not set."
  echo "[push-image] Set AWS_REGION or AWS_DEFAULT_REGION first."
  exit 1
fi

account_id="$(
  aws sts get-caller-identity --query Account --output text --region "${aws_region}"
)"

if [[ -z "${account_id}" || "${account_id}" == "None" ]]; then
  echo "[push-image] Could not resolve AWS account."
  exit 1
fi

registry="${account_id}.dkr.ecr.${aws_region}.amazonaws.com"
image_repo_uri="${registry}/${ECR_REPOSITORY}"
local_image_name="pv-expected-energy-simulation:${version_tag}"

echo "[push-image] Logging in to ${registry}"
aws ecr get-login-password --region "${aws_region}" |
  docker login --username AWS --password-stdin "${registry}"

echo "[push-image] Building Lambda-compatible image ${local_image_name}"
# Lambda rejects the image indexes/attestations that `buildx --push` can emit.
# Build a single ARM64 image locally, then push plain image tags to ECR.
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --build-arg "CODEARTIFACT_TOKEN=${AWS_CODEARTIFACT_TOKEN}" \
  --load \
  --file "${PROJECT_ROOT}/Dockerfile" \
  --tag "${local_image_name}" \
  "${PROJECT_ROOT}"

echo "[push-image] Tagging ${image_repo_uri}:${version_tag}"
docker tag "${local_image_name}" "${image_repo_uri}:${version_tag}"

echo "[push-image] Tagging ${image_repo_uri}:latest"
docker tag "${local_image_name}" "${image_repo_uri}:latest"

echo "[push-image] Pushing ${image_repo_uri}:${version_tag}"
docker push "${image_repo_uri}:${version_tag}"

echo "[push-image] Pushing ${image_repo_uri}:latest"
docker push "${image_repo_uri}:latest"
