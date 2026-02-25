#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

get_openapi_typescript_version() {
  node -e '
const fs = require("fs");
const lock = JSON.parse(fs.readFileSync("package-lock.json", "utf8"));
const version =
  lock?.packages?.["node_modules/openapi-typescript"]?.version ??
  lock?.dependencies?.["openapi-typescript"]?.version;
if (!version) {
  console.error("Could not find openapi-typescript version in package-lock.json");
  process.exit(1);
}
process.stdout.write(version);
'
}

get_openapi_python_dependency_versions() {
  uv run python - <<'PY'
from importlib import metadata

deps = ("fastapi", "pydantic", "starlette")
parts = []
for dep in deps:
    try:
        version = metadata.version(dep)
    except metadata.PackageNotFoundError:
        version = "not-installed"
    parts.append(f"{dep}={version}")
print(", ".join(parts))
PY
}

echo "Using toolchain versions:"
echo "  uv: $(uv --version)"
echo "  node: $(node --version)"
echo "  npx: $(npx --version)"
pushd "${SCRIPT_DIR}/../api" >/dev/null
echo "  python (uv run): $(uv run python -V 2>&1)"
OPENAPI_PYTHON_DEPENDENCY_VERSIONS="$(
  get_openapi_python_dependency_versions
)"
echo "  openapi-python-deps: ${OPENAPI_PYTHON_DEPENDENCY_VERSIONS}"
popd >/dev/null

echo "Generating OpenAPI schema..."
pushd "${SCRIPT_DIR}/../api" >/dev/null
uv run _scripts/generate_openapi_spec.py
popd >/dev/null
echo "OpenAPI schema generated"

echo "Generating TypeScript types..."
pushd "${SCRIPT_DIR}/../web-app" >/dev/null
OPENAPI_TYPESCRIPT_VERSION="$(get_openapi_typescript_version)"
echo "  openapi-typescript: ${OPENAPI_TYPESCRIPT_VERSION} (package-lock)"
npx "openapi-typescript@${OPENAPI_TYPESCRIPT_VERSION}" \
  ../api/openapi.json \
  -o ./src/api/schema.d.ts
popd >/dev/null
echo "TypeScript types generated"

echo "Keeping OpenAPI schema for CI checks..."

echo "Generating TypeScript enums..."
pushd "${SCRIPT_DIR}/../api" >/dev/null
uv run _scripts/generate_ts_enums.py
popd >/dev/null
echo "TypeScript enums generated"

echo "Done"
