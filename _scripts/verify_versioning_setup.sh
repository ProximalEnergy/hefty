#!/bin/bash

# Script to verify the versioning setup is working correctly
# This checks that all scripts, workflows, and configurations are properly set up

set -e

echo "🔍 Verifying Core and API Versioning Setup..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
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

# Check 1: Core workflow file exists
echo "📋 Checking Core workflow..."
if [ -f "$MONO_ROOT/.github/workflows/core-publish.yml" ]; then
    success "Core publish workflow exists"

    # Check it has all three branches
    if grep -q "\- dev" "$MONO_ROOT/.github/workflows/core-publish.yml" && \
       grep -q "\- staging" "$MONO_ROOT/.github/workflows/core-publish.yml" && \
       grep -q "\- main" "$MONO_ROOT/.github/workflows/core-publish.yml"; then
        success "Core workflow configured for dev, staging, and main branches"
    else
        error "Core workflow missing branch configurations"
    fi
else
    error "Core publish workflow not found at .github/workflows/core-publish.yml"
fi

# Check 2: API deployment workflow
echo ""
echo "📋 Checking API deployment workflow..."
if [ -f "$MONO_ROOT/.github/workflows/api-deploy.yml" ]; then
    success "API deploy workflow exists"

    # Check it has version type configuration
    if grep -q "CORE_VERSION_TYPE=beta" "$MONO_ROOT/.github/workflows/api-deploy.yml" && \
       grep -q "CORE_VERSION_TYPE=rc" "$MONO_ROOT/.github/workflows/api-deploy.yml" && \
       grep -q "CORE_VERSION_TYPE=stable" "$MONO_ROOT/.github/workflows/api-deploy.yml"; then
        success "API workflow configured with core version types"
    else
        error "API workflow missing CORE_VERSION_TYPE configurations"
    fi
else
    error "API deploy workflow not found at .github/workflows/api-deploy.yml"
fi

# Check 3: API scripts exist and are executable
echo ""
echo "📋 Checking API scripts..."
SCRIPTS=(
    "$MONO_ROOT/api/_scripts/update_core_version.sh"
    "$MONO_ROOT/api/_scripts/update_core_auto.sh"
    "$MONO_ROOT/api/_scripts/auth_aws_codeartifact.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            success "$(basename "$script") exists and is executable"
        else
            warning "$(basename "$script") exists but is not executable"
            info "Run: chmod +x $script"
        fi
    else
        error "$(basename "$script") not found"
    fi
done

# Check 4: API .mise.toml has tasks
echo ""
echo "📋 Checking API mise tasks..."
if [ -f "$MONO_ROOT/api/.mise.toml" ]; then
    if grep -q "core_auto" "$MONO_ROOT/api/.mise.toml" && \
       grep -q "core_beta" "$MONO_ROOT/api/.mise.toml" && \
       grep -q "core_rc" "$MONO_ROOT/api/.mise.toml" && \
       grep -q "core_stable" "$MONO_ROOT/api/.mise.toml"; then
        success "API .mise.toml has core version tasks"
    else
        error "API .mise.toml missing core version tasks"
    fi
else
    error "API .mise.toml not found"
fi

# Check 5: Core pyproject.toml has version
echo ""
echo "📋 Checking Core configuration..."
if [ -f "$MONO_ROOT/core/pyproject.toml" ]; then
    CORE_VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('$MONO_ROOT/core/pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$CORE_VERSION" ]; then
        success "Core version: $CORE_VERSION"
    else
        error "Could not read core version from pyproject.toml"
    fi

    # Check for bump task
    if [ -f "$MONO_ROOT/core/.mise.toml" ] && grep -q "tasks.bump" "$MONO_ROOT/core/.mise.toml"; then
        success "Core has version bump task"
    else
        warning "Core .mise.toml missing bump task"
    fi
else
    error "Core pyproject.toml not found"
fi

# Check 6: Documentation exists
echo ""
echo "📋 Checking documentation..."
DOCS=(
    "$MONO_ROOT/VERSIONING.md"
    "$MONO_ROOT/VERSIONING_QUICKREF.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        success "$(basename "$doc") exists"
    else
        warning "$(basename "$doc") not found"
    fi
done

# Check 7: Git branches exist
echo ""
echo "📋 Checking git branches..."
cd "$MONO_ROOT"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ $? -eq 0 ]; then
    success "Current branch: $CURRENT_BRANCH"

    # Check if key branches exist
    for branch in dev staging main; do
        if git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null || \
           git show-ref --verify --quiet "refs/remotes/origin/$branch" 2>/dev/null; then
            success "Branch '$branch' exists"
        else
            warning "Branch '$branch' not found (may be normal if not yet created)"
        fi
    done
else
    error "Not in a git repository"
fi

# Check 8: Test AWS authentication (if available)
echo ""
echo "📋 Testing AWS CodeArtifact authentication..."
if command -v aws >/dev/null 2>&1; then
    success "AWS CLI is installed"

    # Try to authenticate (but don't fail if it doesn't work - might be expected locally)
    cd "$MONO_ROOT/api"
    if source _scripts/auth_aws_codeartifact.sh 2>/dev/null; then
        success "AWS CodeArtifact authentication successful"
    else
        warning "AWS CodeArtifact authentication failed (this is normal if AWS credentials are not configured locally)"
        info "Authentication will work in CI/CD environments"
    fi
else
    warning "AWS CLI not installed (required for core version updates)"
    info "Install with: brew install awscli"
fi

# Check 9: Test mise command availability
echo ""
echo "📋 Checking mise availability..."
cd "$MONO_ROOT/api"
if command -v mise >/dev/null 2>&1; then
    success "mise is available"

    # Try listing tasks
    if mise tasks >/dev/null 2>&1; then
        success "mise tasks are accessible"
    else
        warning "mise tasks might not be accessible"
    fi
else
    warning "mise not found in PATH"
    info "Install mise with: curl https://mise.run | sh"
fi

# Summary
echo ""
echo "════════════════════════════════════════════════════════════"
echo "                    VERIFICATION SUMMARY"
echo "════════════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Versioning setup is complete.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test locally: cd api && mise run core_auto"
    echo "  2. Make a change and push to dev branch"
    echo "  3. Verify core publishes as beta version"
    echo "  4. Check API deployment uses beta core"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Setup complete with $WARNINGS warning(s).${NC}"
    echo "Review warnings above. Most are informational and may be expected."
    exit 0
else
    echo -e "${RED}✗ Found $ERRORS error(s) and $WARNINGS warning(s).${NC}"
    echo "Please address the errors above before proceeding."
    exit 1
fi
