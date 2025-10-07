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

# Copy core library source
echo "2. Copying core library..."
mkdir -p core
cp -r "$CORE_DIR/src/core"/* core/
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

if [ -f "core/models.py" ]; then
    echo "   ✓ core/models.py found"
else
    echo "   ❌ core/models.py NOT found"
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

# Generate requirements.txt (if uv is available)
echo ""
if command -v uv >/dev/null 2>&1; then
    echo "4. Generating requirements.txt..."
    cd "$API_DIR"
    uv export --frozen --no-emit-workspace --no-dev --no-editable -o "$TEST_DIR/api/requirements.txt" --no-hashes 2>/dev/null || true

    if [ -f "$TEST_DIR/api/requirements.txt" ]; then
        # Remove core from requirements
        sed '/^core==/d' "$TEST_DIR/api/requirements.txt" > "$TEST_DIR/api/requirements.tmp"
        mv "$TEST_DIR/api/requirements.tmp" "$TEST_DIR/api/requirements.txt"

        # Check that core is not in requirements
        if grep -q "^core==" "$TEST_DIR/api/requirements.txt"; then
            echo "   ❌ core still in requirements.txt!"
            exit 1
        else
            echo "   ✓ requirements.txt generated without core dependency"
        fi

        echo ""
        echo "   Requirements file size: $(wc -l < "$TEST_DIR/api/requirements.txt") lines"
    fi
else
    echo "4. Skipping requirements.txt generation (uv not installed)"
fi

# Create deployment package
echo ""
echo "5. Creating deployment package..."
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
echo "6. Verifying package contents..."
echo ""
echo "   Checking for required files..."

REQUIRED_FILES=(
    "app/"
    "core/"
    "core/__init__.py"
    "core/models.py"
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
echo "7. Package Summary:"
echo ""
unzip -l "$TEST_DIR/deploy.zip" | head -30
echo "   ..."
echo ""
FILE_COUNT=$(unzip -l "$TEST_DIR/deploy.zip" | tail -1 | awk '{print $2}')
echo "   Total files in package: $FILE_COUNT"
echo "   Package size: $PACKAGE_SIZE"

# Test Python structure (imports will fail without dependencies, which is expected)
echo ""
echo "8. Testing Python structure..."
cd "$TEST_DIR/api"

# Just verify the structure is valid Python
if python3 -c "import sys; import ast; ast.parse(open('core/__init__.py').read())" 2>/dev/null; then
    echo "   ✓ core/__init__.py has valid Python syntax"
else
    echo "   ❌ core/__init__.py has syntax errors"
    exit 1
fi

if python3 -c "import sys; import ast; ast.parse(open('core/models.py').read())" 2>/dev/null; then
    echo "   ✓ core/models.py has valid Python syntax"
else
    echo "   ❌ core/models.py has syntax errors"
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
