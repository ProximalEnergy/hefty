#!/bin/bash

# Print files changed vs a base ref, plus local staged/unstaged changes.

set -euo pipefail

base_ref="${1:-dev}"

if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
    echo "Base ref '${base_ref}' not found." >&2
    exit 1
fi

{
    git diff --name-only "${base_ref}...HEAD"
    git diff --name-only HEAD
} | sort -u
