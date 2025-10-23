#!/bin/bash

# Script to run both API and web-app in development mode using mise
# Shows logs from both services with prefixes

set -e

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
  mise run web:preview 2>&1 | \
    while IFS= read -r line; do
      echo -e "${GREEN}[WEB]${NC} $line"
    done
) &

# Wait for all background processes
wait
