#!/usr/bin/env bash

set -euo pipefail

mise run pveem:types
mise run pveem:ruff
mise run pveem:pytest
mise run pveem:cdk-deploy
