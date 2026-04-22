#!/bin/bash

set -e

echo "🔍 Verifying Core and API deploy setup..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ERRORS=0
WARNINGS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() {
    echo -e "${RED}✗ ERROR:${NC} $1"
    ((ERRORS++))
}

warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
    ((WARNINGS++))
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "📋 Checking deploy workflow..."
DEPLOY_WORKFLOW="$MONO_ROOT/.github/workflows/deploy-composite.yml"
if [ -f "$DEPLOY_WORKFLOW" ]; then
    success "deploy-composite.yml exists"

    if grep -q -- "--no-emit-package core" "$DEPLOY_WORKFLOW"; then
        success "API requirements export omits bundled core"
    else
        error "Deploy workflow does not omit core from requirements.txt"
    fi

    if grep -q "cp -R core/src/core/. api/core/" "$DEPLOY_WORKFLOW"; then
        success "Deploy workflow bundles workspace core into api/core"
    else
        error "Deploy workflow does not bundle workspace core"
    fi

    if grep -q "uv build --wheel --out-dir" "$DEPLOY_WORKFLOW" && \
       grep -q "core-\\*\\.dist-info" "$DEPLOY_WORKFLOW"; then
        success "Deploy workflow preserves core distribution metadata"
    else
        error "Deploy workflow does not preserve core dist-info metadata"
    fi
else
    error "Deploy workflow not found at .github/workflows/deploy-composite.yml"
fi

echo ""
echo "📋 Checking obsolete API core scripts are removed..."
OBSOLETE_SCRIPTS=(
    "$MONO_ROOT/api/_scripts/update_core.sh"
    "$MONO_ROOT/api/_scripts/aws_core_wrapper.py"
    "$MONO_ROOT/api/_scripts/update_core_version.sh"
    "$MONO_ROOT/api/_scripts/update_core_auto.sh"
)

for script in "${OBSOLETE_SCRIPTS[@]}"; do
    if [ -e "$script" ]; then
        error "$(basename "$script") should be removed"
    else
        success "$(basename "$script") is absent"
    fi
done

echo ""
echo "📋 Checking API tasks..."
MISE_FILE="$MONO_ROOT/.mise.toml"
if [ -f "$MISE_FILE" ]; then
    if grep -q '\[tasks\."api:freeze"\]' "$MISE_FILE"; then
        success "api:freeze task exists"
    else
        error "api:freeze task missing from .mise.toml"
    fi

    if grep -q '\[tasks\."api:test_deploy"\]' "$MISE_FILE"; then
        success "api:test_deploy task exists"
    else
        error "api:test_deploy task missing from .mise.toml"
    fi
else
    error ".mise.toml not found"
fi

echo ""
echo "📋 Checking local test helper..."
TEST_SCRIPT="$MONO_ROOT/api/_scripts/test_deployment_package.sh"
if [ -f "$TEST_SCRIPT" ]; then
    success "test_deployment_package.sh exists"
    if [ -x "$TEST_SCRIPT" ]; then
        success "test_deployment_package.sh is executable"
    else
        warning "test_deployment_package.sh is not executable"
        info "Run: chmod +x $TEST_SCRIPT"
    fi
else
    error "test_deployment_package.sh not found"
fi

echo ""
echo "📋 Checking Core configuration..."
CORE_PYPROJECT="$MONO_ROOT/core/pyproject.toml"
if [ -f "$CORE_PYPROJECT" ]; then
    CORE_VERSION=$(
        python3 -c \
            "import tomllib; print(tomllib.load(open('$CORE_PYPROJECT', 'rb'))['project']['version'])" \
            2>/dev/null
    )
    if [ $? -eq 0 ] && [ -n "$CORE_VERSION" ]; then
        success "Core version: $CORE_VERSION"
    else
        error "Could not read core version from core/pyproject.toml"
    fi
else
    error "core/pyproject.toml not found"
fi

echo ""
echo "📋 Checking API documentation..."
API_README="$MONO_ROOT/api/README.md"
if [ -f "$API_README" ]; then
    success "api/README.md exists"

    if grep -q "bundled directly" "$API_README"; then
        success "README documents bundled-core deployment"
    else
        warning "README does not mention bundled-core deployment"
    fi

    if grep -q "workspace dependency" "$API_README"; then
        success "README documents workspace core for local development"
    else
        warning "README does not mention workspace core for local development"
    fi
else
    warning "api/README.md not found"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "                    VERIFICATION SUMMARY"
echo "════════════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: mise run api:test_deploy"
    echo "  2. Run: mise run api:freeze"
    echo "  3. Confirm deploy-composite.yml packages bundled core metadata"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Setup complete with $WARNINGS warning(s).${NC}"
    echo "Review warnings above."
    exit 0
else
    echo -e "${RED}✗ Found $ERRORS error(s) and $WARNINGS warning(s).${NC}"
    echo "Please address the errors above before proceeding."
    exit 1
fi
