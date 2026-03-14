#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

get_openapi_typescript_version() {
  node -e '
const fs = require("fs");
const installedPath = "node_modules/openapi-typescript/package.json";
if (fs.existsSync(installedPath)) {
  const installed = JSON.parse(fs.readFileSync(installedPath, "utf8"));
  process.stdout.write(installed.version);
  process.exit(0);
}
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
const version = pkg?.devDependencies?.["openapi-typescript"];
if (!version) {
  console.error("Could not find openapi-typescript in web-app/package.json");
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
echo "  pnpm: $(pnpm --version)"
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
echo "  openapi-typescript: ${OPENAPI_TYPESCRIPT_VERSION}"
pnpm exec openapi-typescript \
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
