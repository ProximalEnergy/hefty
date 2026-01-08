#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/.." && pwd)
app_dir="${repo_root}/api/app"

get_matches=$(rg -U -P --glob '*.py' \
  '\.get(?!_async)\s*\([^)]*\boutput_type\s*=' \
  "$app_dir" | cut -d: -f1-2 || true)

if [[ -n "$get_matches" ]]; then
  printf '%s\n' "$get_matches"
  exit 1
fi
