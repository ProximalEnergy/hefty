#!/usr/bin/env bash

set -euo pipefail

# 1. Configuration for Codex
ROOT_DIR="/workspace/mono"
export PATH="$HOME/.local/bin:$PATH"

echo "trying mise trust"
mise trust

echo "Checking system packages..."
if command -v apt-get >/dev/null 2>&1; then
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update -y
    apt-get install -y curl git jq ripgrep
  elif command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y curl git jq ripgrep
  else
    apt-get update -y
    apt-get install -y curl git jq ripgrep
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"




if ! command -v node >/dev/null 2>&1; then
  echo "Node.js not found. Install Node.js before running web-app commands."
fi

if [ -d "$ROOT_DIR" ]; then
  cd "$ROOT_DIR"
  echo "Syncing project dependencies in $ROOT_DIR..."

  uv sync
  uv sync --directory core
  uv sync --directory api
  mise run web:install
  mise run web:plotly
else
  echo "Error: Directory $ROOT_DIR not found."
  exit 1
fi

echo "-------------------------------------------"
echo "Setup complete. Run: ./_scripts/run_checks.sh"
