#!/bin/bash

set -euo pipefail

echo "Generating OpenAPI schema..."
pushd "$(dirname "$0")/../api"
uv run _scripts/generate_openapi_spec.py
popd
echo "OpenAPI schema generated"

echo "Generating TypeScript types..."
pushd "$(dirname "$0")/../web-app"
# Use pinned version if provided (e.g., from CI), otherwise use default
if [ -n "${OPENAPI_TYPESCRIPT_VERSION:-}" ]; then
  npx "openapi-typescript@${OPENAPI_TYPESCRIPT_VERSION}" ../api/openapi.json -o ./src/api/schema.d.ts
else
  npx openapi-typescript ../api/openapi.json -o ./src/api/schema.d.ts
fi
popd
echo "TypeScript types generated"

echo "Removing OpenAPI schema..."
rm -f "$(dirname "$0")/../api/openapi.json"
echo "OpenAPI schema removed"

echo "Generating TypeScript enums..."
pushd "$(dirname "$0")/../api"
uv run _scripts/generate_ts_enums.py
popd
echo "TypeScript enums generated"

echo "Done"