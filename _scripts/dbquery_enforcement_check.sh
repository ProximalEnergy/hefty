#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BASELINE_FILE="${SCRIPT_DIR}/ast-grep/dbquery-baseline.txt"
TMP_OUTPUT="$(mktemp)"
trap 'rm -f "${TMP_OUTPUT}"' EXIT

cd "${REPO_ROOT}"

scan_targets=("core/src" "api/app" "microservices" "pv-eem/src")

# Scan for SQLAlchemy-style CRUD execution calls.
uvx --from ast-grep-cli ast-grep scan \
  --inline-rules '
id: sqlalchemy-db-crud-outside-dbquery
language: Python
rule:
  pattern: $OBJ.$METHOD($$$ARGS)
constraints:
  METHOD:
    regex: "^(add_all|delete|execute|scalar|scalars|flush|commit|bulk_save_objects|bulk_insert_mappings|bulk_update_mappings|exec_driver_sql|query)$"
message: "Use DbQuery for DB CRUD operations"
severity: warning
---
id: sqlalchemy-db-crud-outside-dbquery-specific
language: Python
rule:
  any:
    - pattern: $SESSION.add($$$ARGS)
    - pattern: $SESSION.get($$$ARGS)
    - pattern: $SESSION.merge($$$ARGS)
    - pattern: $QUERY.update($$$ARGS)
constraints:
  SESSION:
    regex: "^(self\\.)?[a-zA-Z0-9_]*(session|db)[a-zA-Z0-9_]*$"
  QUERY:
    regex: "^(self\\.)?[a-zA-Z0-9_]*(query|stmt)[a-zA-Z0-9_]*$"
message: "Use DbQuery for DB CRUD operations"
severity: warning
---
id: sqlalchemy-no-return-first
language: Python
rule:
  pattern: return $QUERY.first()
message: "return $QUERY.first() is banned. Use DbQuery instead."
severity: warning
---
id: sqlalchemy-no-return-one-or-none
language: Python
rule:
  pattern: return $QUERY.one_or_none()
message: "return $QUERY.one_or_none() is banned. Use DbQuery instead."
severity: warning
---
id: sqlalchemy-no-return-scalar-one
language: Python
rule:
  pattern: return $QUERY.scalar_one()
message: "return $QUERY.scalar_one() is banned. Use DbQuery instead."
severity: warning
' \
  --json=stream \
  "${scan_targets[@]}" \
  --globs '!**/tests/**' \
  --globs '!**/scripts/**' \
  --globs '!**/migrations/**' \
  --globs '!**/dbquery/**' \
  --globs '!**/*dbquery*.py' \
  --globs '!**/*db_query*.py' \
  > "${TMP_OUTPUT}"

python3 - <<'PY' "${TMP_OUTPUT}" "${BASELINE_FILE}"
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from collections import Counter, defaultdict

results_path = pathlib.Path(sys.argv[1])
baseline_path = pathlib.Path(sys.argv[2])

current: Counter[str] = Counter()
violation_lines: dict[str, list[int]] = defaultdict(list)

for line in results_path.read_text().splitlines():
    stripped = line.strip()
    if not stripped:
        continue
    data = json.loads(stripped)
    file_path = data["file"]
    rule_id = data["ruleId"]
    if rule_id == "sqlalchemy-db-crud-outside-dbquery-specific":
        rule_id = "sqlalchemy-db-crud-outside-dbquery"

    match_text = data.get("text", "")
    text_hash = hashlib.sha256(match_text.encode("utf-8")).hexdigest()[:8]
    snippet = " ".join(match_text.split())[:100].strip()

    key = f"{file_path}:{rule_id}:{text_hash}:{snippet}"
    current[key] += 1

    line_num = data.get("range", {}).get("start", {}).get("line", 0) + 1
    violation_lines[key].append(line_num)

baseline: Counter[str] = Counter()
if baseline_path.exists():
    for line in baseline_path.read_text().splitlines():
        line = line.strip()
        if line:
            baseline[line] += 1

diff = current - baseline
new_violations = sorted(diff.elements())

if new_violations:
    print("New DbQuery enforcement violations detected:")
    seen = set()
    unique_violations = []
    for v in new_violations:
        if v not in seen:
            seen.add(v)
            unique_violations.append(v)
            
    for violation in unique_violations:
        lines = violation_lines.get(violation, [])
        lines_str = ",".join(str(l) for l in sorted(set(lines)))
        
        parts = violation.split(":", 1)
        for _ in range(diff[violation]):
            print(f"{parts[0]}:{lines_str}:{parts[1]}")
    raise SystemExit(1)

print("DbQuery enforcement check passed (no new violations).")
PY
