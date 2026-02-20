#!/usr/bin/env bash

set -u
set -o pipefail

LOG_FILE="$(mktemp -t cdk-deploy-log.XXXXXX)"
ARGS=()
skip_next=0

for arg in "$@"; do
  if [[ "${skip_next}" -eq 1 ]]; then
    skip_next=0
    continue
  fi

  if [[ "${arg}" == --require-approval ]]; then
    skip_next=1
    continue
  fi

  if [[ "${arg}" == --require-approval=* ]]; then
    continue
  fi

  ARGS+=("${arg}")
done

ARGS+=(--require-approval never)
echo "[cdk-deploy] Enforcing approval mode: never"

cleanup() {
  rm -f "${LOG_FILE}"
}
trap cleanup EXIT

echo "[cdk-deploy] Running: cd events && uv run cdk deploy ${ARGS[*]}"

if (cd events && uv run cdk deploy "${ARGS[@]}") 2>&1 | tee "${LOG_FILE}"; then
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

if grep -qi "requires approval" "${LOG_FILE}"; then
  echo "[cdk-deploy] Hint: deployment requested approval."
  echo "[cdk-deploy] Re-run with: mise run pveem:cdk-deploy -- --require-approval never"
fi

echo "[cdk-deploy] Last 60 lines of CDK output:"
tail -n 60 "${LOG_FILE}"

exit "${status}"
