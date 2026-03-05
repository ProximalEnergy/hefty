#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

uv run --project "${ROOT_DIR}/kpi" --directory "${ROOT_DIR}/kpi" --dev -- bash -lc '
  mypy src/kpi_pipeline &&
  mypy lambda_function.py &&
  python -m kpi_pipeline.services.calc &&
  python -m kpi_pipeline.services.process
'
