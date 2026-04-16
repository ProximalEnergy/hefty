#!/usr/bin/env bash

set -euo pipefail

mise run pveem:check
mise run pveem:cdk-deploy
