#!/bin/bash
# Script to run both API and web-app in development mode using mise
# Shows logs from both services with prefixes
set -e

# Colors and styles for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BG_RED='\033[41m'      # Red background
BG_YELLOW='\033[43m'   # Yellow background
NC='\033[0m' # No Color

echo -e "${GREEN}Starting development servers...${NC}"

# Trap to kill all background processes on exit
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Run API server in background and prefix output
(
  mise run api:run 2>&1 | \
    while IFS= read -r line; do
      # Highlight Warning and 404 with red background
      highlighted_line=$(echo "$line" | \
        sed -E "s/(Warning|warn|404 Not Found)/\x1b[41m\1\x1b[0m/g")
      echo -e "${YELLOW}[API]${NC} $highlighted_line"
    done
) &

# Run web-app dev server in background and prefix output
(
  mise run web:dev 2>&1 | \
    while IFS= read -r line; do
      # Highlight Warning and 404 with red background
      highlighted_line=$(echo "$line" | \
        sed -E "s/(Warning|404)/\x1b[41m\1\x1b[0m/g")
      echo -e "${GREEN}[WEB]${NC} $highlighted_line"
    done
) &

# Wait for all background processes
wait
