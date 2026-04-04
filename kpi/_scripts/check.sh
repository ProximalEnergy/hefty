#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

uv run --project "${ROOT_DIR}/kpi" --directory "${ROOT_DIR}/kpi" --dev -- \
  mypy src/kpi lambda_function.py
