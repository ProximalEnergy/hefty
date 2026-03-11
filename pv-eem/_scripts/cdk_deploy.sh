#!/usr/bin/env bash

set -eu
set -o pipefail

LOG_FILE="$(mktemp -t cdk-deploy-log.XXXXXX)"
ARGS=()
skip_next=0
pending_context=0
has_image_tag=0
has_runtime_environment=0

echo "[cdk-deploy] Pushing image before deploy"
bash _scripts/push_image.sh

for arg in "$@"; do
  if [[ "${skip_next}" -eq 1 ]]; then
    skip_next=0
    continue
  fi

  if [[ "${pending_context}" -eq 1 ]]; then
    if [[ "${arg}" == imageTag=* ]]; then
      has_image_tag=1
    fi
    if [[ "${arg}" == runtimeEnvironment=* ]]; then
      has_runtime_environment=1
    fi
    pending_context=0
    ARGS+=("${arg}")
    continue
  fi

  if [[ "${arg}" == --require-approval ]]; then
    skip_next=1
    continue
  fi

  if [[ "${arg}" == --require-approval=* ]]; then
    continue
  fi

  if [[ "${arg}" == "-c" || "${arg}" == "--context" ]]; then
    pending_context=1
    ARGS+=("${arg}")
    continue
  fi

  if [[ "${arg}" == --context=* ]]; then
    if [[ "${arg#*=}" == imageTag=* ]]; then
      has_image_tag=1
    fi
    if [[ "${arg#*=}" == runtimeEnvironment=* ]]; then
      has_runtime_environment=1
    fi
    ARGS+=("${arg}")
    continue
  fi

  ARGS+=("${arg}")
done

if [[ "${has_image_tag}" -eq 0 ]]; then
  image_tag="$(
    grep '^version = "' pyproject.toml |
      head -n 1 |
      sed 's/version = "\(.*\)"/\1/'
  )"

  if [[ -z "${image_tag}" ]]; then
    echo "[cdk-deploy] Could not read version from pyproject.toml."
    exit 1
  fi

  ARGS+=(-c "imageTag=${image_tag}")
  echo "[cdk-deploy] Defaulting imageTag to ${image_tag}"
fi

if [[ "${has_runtime_environment}" -eq 0 ]]; then
  ARGS+=(-c "runtimeEnvironment=PROD")
  echo "[cdk-deploy] Defaulting runtimeEnvironment to PROD"
fi

ARGS+=(--require-approval never)
echo "[cdk-deploy] Enforcing approval mode: never"

cleanup() {
  rm -f "${LOG_FILE}"
}
trap cleanup EXIT

echo "[cdk-deploy] Running: cd _cdk && uv run cdk deploy ${ARGS[*]}"

if (cd _cdk && uv run cdk deploy "${ARGS[@]}") 2>&1 | tee "${LOG_FILE}"; then
  exit 0
fi

status=${PIPESTATUS[0]}
echo "[cdk-deploy] Deploy failed with exit code ${status}."

if grep -qiE "Unable to resolve AWS account|NoCredentialProviders|credential" \
  "${LOG_FILE}"; then
  echo "[cdk-deploy] Hint: AWS credentials are missing or invalid."
  echo "[cdk-deploy] Run: aws sts get-caller-identity"
fi

if grep -qi "bootstrap stack version" "${LOG_FILE}"; then
  echo "[cdk-deploy] Hint: CDK bootstrap may be missing for this account/region."
  echo "[cdk-deploy] Run: cdk bootstrap aws://<account>/<region>"
fi

if grep -qi "image manifest, config or layer media type" "${LOG_FILE}"; then
  echo "[cdk-deploy] Hint: the ECR tag is not Lambda-compatible."
  echo "[cdk-deploy] Rebuild and repush with: mise run pveem:push-image"
  echo "[cdk-deploy] Then delete the ROLLBACK_COMPLETE stack and redeploy."
fi

if grep -qi "requires approval" "${LOG_FILE}"; then
  echo "[cdk-deploy] Hint: deployment requested approval."
  echo "[cdk-deploy] Re-run with: mise run pveem:cdk-deploy -- --require-approval never"
fi

echo "[cdk-deploy] Last 60 lines of CDK output:"
tail -n 60 "${LOG_FILE}"

exit "${status}"
