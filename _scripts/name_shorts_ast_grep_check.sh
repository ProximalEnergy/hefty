#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TMP_OUTPUT="$(mktemp)"
trap 'rm -f "${TMP_OUTPUT}"' EXIT

cd "${REPO_ROOT}"

scan_targets=(
    "core/src"
    "api/app"
    "issues"
    "microservices"
    "pv-eem/src"
    "web-app/src"
)

INLINE_RULES="$(cat <<'YAML'
id: python-hardcoded-name-shorts-array
language: Python
rule:
  any:
    - pattern: $NAME = $VALUE
    - pattern:
        context: foo($NAME=$VALUE)
        selector: keyword_argument
constraints:
  NAME:
    regex: ".*_name_shorts?$"
  VALUE:
    kind: list
    has:
      kind: string
message: "Use enum/constants instead of hardcoded name_short strings"
severity: warning
---
id: python-hardcoded-name-short-assignment
language: Python
rule:
  any:
    - pattern: $NAME = $VALUE
    - pattern:
        context: foo($NAME=$VALUE)
        selector: keyword_argument
constraints:
  NAME:
    regex: ".*_?name_short$"
  VALUE:
    kind: string
message: "Use enum/constants instead of hardcoded name_short strings"
severity: warning
---
id: ts-hardcoded-name-shorts-array
language: TypeScript
rule:
  any:
    - pattern: $NAME = $VALUE
    - pattern: const $NAME = $VALUE
    - pattern: let $NAME = $VALUE
    - pattern: var $NAME = $VALUE
    - pattern:
        context: "{ $NAME: $VALUE }"
        selector: pair
constraints:
  NAME:
    regex: ".*[Nn]ame_?[Ss]horts?$"
  VALUE:
    kind: array
    has:
      kind: string
message: "Use enum/constants instead of hardcoded name_short strings"
severity: warning
---
id: ts-hardcoded-name-short-assignment
language: TypeScript
rule:
  any:
    - pattern: $NAME = $VALUE
    - pattern: const $NAME = $VALUE
    - pattern: let $NAME = $VALUE
    - pattern: var $NAME = $VALUE
    - pattern:
        context: "{ $NAME: $VALUE }"
        selector: pair
constraints:
  NAME:
    regex: ".*[Nn]ame_?[Ss]hort$"
  VALUE:
    kind: string
message: "Use enum/constants instead of hardcoded name_short strings"
severity: warning
YAML
)"

uvx --from ast-grep-cli ast-grep scan \
  --inline-rules "${INLINE_RULES}" \
  --json=stream \
  "${scan_targets[@]}" \
  --globs '!**/node_modules/**' \
  --globs '!**/.next/**' \
  --globs '!**/dist/**' \
  --globs '!**/build/**' \
  --globs '!**/__pycache__/**' \
  --globs '!**/.venv/**' \
  --globs '!**/venv/**' \
  --globs '!**/.mypy_cache/**' \
  --globs '!**/.ruff_cache/**' \
  --globs '!**/.pytest_cache/**' \
  --globs '!**/*.egg-info/**' \
  --globs '!api/app/_data_insert/**' \
  --globs '!api/app/_tests/**' \
  --globs '!issues/tests/**' \
  --globs '!pv-eem/_scripts/**' \
  --globs '!pv-eem/_tests/**' \
  --globs '!web-app/src/api/schema.d.ts' \
  > "${TMP_OUTPUT}"

python3 - <<'PY' "${TMP_OUTPUT}"
from __future__ import annotations

import json
import pathlib
import re
import sys

IGNORE_PATTERN = re.compile(
    r"(#|//).*(noqa.*hardcoded.*name.*short|allow.*hardcoded.*name.*short)",
    re.IGNORECASE,
)


def has_ignore_comment(*, file_path: str, line_num: int) -> bool:
    try:
        lines = pathlib.Path(file_path).read_text().splitlines()
    except OSError:
        return False

    indexes = [line_num - 1, line_num - 2]
    for idx in indexes:
        if idx < 0 or idx >= len(lines):
            continue
        if IGNORE_PATTERN.search(lines[idx]):
            return True
    return False


raw = pathlib.Path(sys.argv[1]).read_text().splitlines()
violations: list[str] = []
for line in raw:
    stripped = line.strip()
    if not stripped:
        continue
    data = json.loads(stripped)
    file_path = data.get("file", "")
    line_num = data.get("range", {}).get("start", {}).get("line", -1) + 1
    if has_ignore_comment(file_path=file_path, line_num=line_num):
        continue
    text = " ".join(data.get("text", "").split())
    rule_id = data.get("ruleId", "unknown")
    violations.append(f"{file_path}:{line_num}:{rule_id}: {text}")

if violations:
    print("Found hardcoded name_short/name_shorts usages:")
    for violation in violations:
        print(violation)
    raise SystemExit(1)

print("Hardcoded name_shorts check passed.")
PY
