#!/bin/bash
set -euo pipefail

python3 _scripts/check_lint_config_changes.py "$@"
