#!/bin/bash

# Script to run both API and web-app in development mode using mise
# Shows logs from both services with prefixes

set -e

# Automatically merge latest dev into current branch
echo "Fetching latest dev branch..."
git fetch origin dev:dev 2>/dev/null || git fetch origin dev

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
DEV_COMMIT=$(git rev-parse origin/dev)
MERGE_BASE=$(git merge-base HEAD origin/dev)

if [ "$MERGE_BASE" != "$DEV_COMMIT" ]; then
  echo "Merging origin/dev into $CURRENT_BRANCH..."
  git merge origin/dev --no-edit
  echo "✓ Successfully merged dev into $CURRENT_BRANCH"
else
  echo "✓ Branch is already up to date with dev"
fi

# Ensure core dependency source matches current branch
python3 _scripts/switch_core_source.py

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting development servers...${NC}"

# Trap to kill all background processes on exit
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Run API server in background and prefix output
(
  mise run api:run 2>&1 | \
    while IFS= read -r line; do
      echo -e "${YELLOW}[API]${NC} $line"
    done
) &

# Run web-app dev server in background and prefix output
(
  mise run web-app:dev 2>&1 | \
    while IFS= read -r line; do
      echo -e "${GREEN}[WEB]${NC} $line"
    done
) &

# Wait for all background processes
wait
