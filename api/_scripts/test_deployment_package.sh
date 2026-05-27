#!/bin/bash

# Script to test the deployment package structure locally
# This simulates what the CI/CD pipeline does

set -e

echo "================================"
echo "Testing Deployment Package Setup"
echo "================================"
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(dirname "$SCRIPT_DIR")"
MONO_DIR="$(dirname "$API_DIR")"
CORE_DIR="$MONO_DIR/core"

echo "Project directories:"
echo "  Monorepo: $MONO_DIR"
echo "  API:      $API_DIR"
echo "  Core:     $CORE_DIR"
echo ""

# Check if core directory exists
if [ ! -d "$CORE_DIR/src/core" ]; then
    echo "❌ Error: Core library not found at $CORE_DIR/src/core"
    exit 1
fi

echo "✓ Core library found"
echo ""

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ Error: uv is required to build bundled core metadata"
    exit 1
fi

echo "✓ uv is available"
echo ""

# Create a temporary directory for testing
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

echo "Creating test deployment package in: $TEST_DIR"
echo ""

# Copy API directory to test location
echo "1. Copying API files..."
cp -r "$API_DIR" "$TEST_DIR/api"
cd "$TEST_DIR/api"

# Remove any existing core directory
if [ -d "core" ]; then
    echo "   Removing existing core directory..."
    rm -rf core
fi

find . -maxdepth 1 -type d -name 'core-*.dist-info' -exec rm -rf {} +

# Copy core library source
echo "2. Copying core library..."
mkdir -p core
cp -R "$CORE_DIR/src/core/." core/
echo "   ✓ Core library copied to api/core/"

# Check core structure
echo ""
echo "3. Verifying core structure..."
if [ -f "core/__init__.py" ]; then
    echo "   ✓ core/__init__.py found"
else
    echo "   ❌ core/__init__.py NOT found"
    exit 1
fi

if [ -f "core/models/__init__.py" ]; then
    echo "   ✓ core/models/__init__.py found"
else
    echo "   ❌ core/models/__init__.py NOT found"
    exit 1
fi

if [ -f "core/database.py" ]; then
    echo "   ✓ core/database.py found"
else
    echo "   ❌ core/database.py NOT found"
    exit 1
fi

# List core contents
echo ""
echo "Core library contents:"
ls -la core/ | head -20

echo ""
echo "4. Building bundled core distribution metadata..."
CORE_WHEEL_DIR="$TEST_DIR/core-dist"
mkdir -p "$CORE_WHEEL_DIR"
cd "$CORE_DIR"
uv build --wheel --out-dir "$CORE_WHEEL_DIR"
cd "$TEST_DIR/api"

CORE_WHEEL_PATH="$(
    find "$CORE_WHEEL_DIR" -maxdepth 1 -name 'core-*.whl' | head -n 1
)"
if [ -z "$CORE_WHEEL_PATH" ]; then
    echo "   ❌ core wheel was not built"
    exit 1
fi

unzip -q "$CORE_WHEEL_PATH" 'core-*.dist-info/*' -d "$TEST_DIR/api"

CORE_DIST_INFO_DIR="$(
    find . -maxdepth 1 -type d -name 'core-*.dist-info' | head -n 1
)"
if [ -n "$CORE_DIST_INFO_DIR" ] && [ -f "$CORE_DIST_INFO_DIR/METADATA" ]; then
    echo "   ✓ core dist-info extracted to $CORE_DIST_INFO_DIR"
else
    echo "   ❌ core dist-info NOT found"
    exit 1
fi

# Generate requirements.txt
echo "5. Generating requirements.txt..."
cd "$MONO_DIR"
uv export --project . --package api --frozen --no-dev \
  --no-emit-package api --no-emit-package core \
  -o "$TEST_DIR/api/requirements.txt" \
  --no-hashes 2>/dev/null || true

if [ -f "$TEST_DIR/api/requirements.txt" ]; then
    # Check that workspace packages are not emitted into requirements.txt.
    if grep -E -q \
      '^(api|core)([<=>!~ ]|$)' \
      "$TEST_DIR/api/requirements.txt"; then
        echo "   ❌ workspace packages still in requirements.txt!"
        exit 1
    else
        echo "   ✓ requirements.txt omits workspace package dependencies"
    fi

    if grep -E -q \
      '(^(\.\.?/|/)|@ file:|^-[eE] )' \
      "$TEST_DIR/api/requirements.txt"; then
        echo "   ❌ requirements.txt contains local path or editable refs!"
        exit 1
    else
        echo "   ✓ requirements.txt contains only publishable dependencies"
    fi

    echo ""
    echo "   Requirements file size: $(wc -l < "$TEST_DIR/api/requirements.txt") lines"
fi

# Create deployment package
echo ""
echo "6. Creating deployment package..."
cd "$TEST_DIR/api"
zip -r "$TEST_DIR/deploy.zip" . -x "*.git*" -x ".venv/*" -x "__pycache__/*" -x "*.pyc" >/dev/null 2>&1

if [ -f "$TEST_DIR/deploy.zip" ]; then
    PACKAGE_SIZE=$(du -h "$TEST_DIR/deploy.zip" | cut -f1)
    echo "   ✓ Deployment package created: $PACKAGE_SIZE"
else
    echo "   ❌ Failed to create deployment package"
    exit 1
fi

# Verify package contents
echo ""
echo "7. Verifying package contents..."
echo ""
echo "   Checking for required files..."

REQUIRED_FILES=(
    "app/"
    "core/"
    "core/__init__.py"
    "core/models/"
    "core/models/__init__.py"
    "requirements.txt"
    "Procfile"
    ".ebextensions/"
)

for file in "${REQUIRED_FILES[@]}"; do
    if unzip -l "$TEST_DIR/deploy.zip" | grep -q "$file"; then
        echo "   ✓ $file"
    else
        echo "   ❌ $file NOT FOUND"
        exit 1
    fi
done

if unzip -l "$TEST_DIR/deploy.zip" | grep -E -q 'core-.*dist-info/METADATA'; then
    echo "   ✓ core dist-info metadata"
else
    echo "   ❌ core dist-info metadata NOT FOUND"
    exit 1
fi

echo ""
echo "   Checking for excluded files..."

EXCLUDED_FILES=(
    "_tests/"
    "_pr_checks/"
    "_docs/"
    ".venv/"
    "pyproject.toml"
    "uv.lock"
)

for file in "${EXCLUDED_FILES[@]}"; do
    if unzip -l "$TEST_DIR/deploy.zip" | grep -q "$file"; then
        echo "   ⚠️  $file found (should be excluded)"
    else
        echo "   ✓ $file excluded"
    fi
done

# Show package summary
echo ""
echo "8. Package Summary:"
echo ""
unzip -l "$TEST_DIR/deploy.zip" | head -30
echo "   ..."
echo ""
FILE_COUNT=$(unzip -l "$TEST_DIR/deploy.zip" | tail -1 | awk '{print $2}')
echo "   Total files in package: $FILE_COUNT"
echo "   Package size: $PACKAGE_SIZE"

# Test Python structure (imports will fail without dependencies, which is expected)
echo ""
echo "9. Testing Python structure..."
cd "$TEST_DIR/api"

# Just verify the structure is valid Python
if python3 -c "import sys; import ast; ast.parse(open('core/__init__.py').read())" 2>/dev/null; then
    echo "   ✓ core/__init__.py has valid Python syntax"
else
    echo "   ❌ core/__init__.py has syntax errors"
    exit 1
fi

if find core/models -type f -name '*.py' -print0 | xargs -0 python3 -m py_compile; then
    echo "   ✓ core/models package has valid Python syntax"
else
    echo "   ❌ core/models package has syntax errors"
    exit 1
fi

if python3 -c "import importlib.metadata as m; m.version('core')" \
  >/dev/null 2>&1; then
    echo "   ✓ importlib.metadata.version('core') resolves"
else
    echo "   ❌ importlib.metadata.version('core') does not resolve"
    exit 1
fi

echo "   ℹ️  Full import tests skipped (requires dependencies to be installed)"
echo "      In production, pip will install all dependencies from requirements.txt"

echo ""
echo "================================"
echo "✅ Deployment Package Test PASSED"
echo "================================"
echo ""
echo "The deployment package is ready and contains:"
echo "  • API application code (app/)"
echo "  • Bundled core library (core/)"
echo "  • Bundled core distribution metadata (core-*.dist-info/)"
echo "  • Python dependencies (requirements.txt, without core)"
echo "  • EB configuration (.ebextensions/)"
echo ""
echo "⚠️  Note: Some development files are included in this test."
echo "    The actual CI/CD pipeline will exclude them via .ebignore"
echo ""
echo "To deploy manually:"
echo "  1. Follow steps in DEPLOYMENT.md"
echo "  2. Or use: eb deploy <environment-name>"
echo ""
