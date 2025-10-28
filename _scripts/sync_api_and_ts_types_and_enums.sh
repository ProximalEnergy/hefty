#!/bin/bash

echo "Generating OpenAPI schema..."
pushd "$(dirname "$0")/../api"
uv run _scripts/generate_openapi_spec.py
popd
echo "OpenAPI schema generated"

echo "Generating TypeScript types..."
pushd "$(dirname "$0")/../web-app"
npx openapi-typescript ../api/openapi.json -o ./src/api/schema.d.ts
popd
echo "TypeScript types generated"

echo "Removing OpenAPI schema..."
rm "$(dirname "$0")/../api/openapi.json"
echo "OpenAPI schema removed"

echo "Generating TypeScript enums..."
pushd "$(dirname "$0")/../api"
uv run _scripts/generate_ts_enums.py
popd
echo "TypeScript enums generated"

echo "Done"