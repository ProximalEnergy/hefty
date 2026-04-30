#!/bin/bash
set -eo pipefail

TAB="$(printf '\t')"
CHANGED_FILES_FROM=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --changed-files-from)
            if [ "$#" -lt 2 ]; then
                echo "Missing value for --changed-files-from" >&2
                exit 2
            fi
            CHANGED_FILES_FROM="$2"
            shift 2
            ;;
        --changed-files-from=*)
            CHANGED_FILES_FROM="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [ -n "$CHANGED_FILES_FROM" ] && [ ! -f "$CHANGED_FILES_FROM" ]; then
    echo "Changed files list not found: $CHANGED_FILES_FROM" >&2
    exit 2
fi

collect_matches() {
    local rules

    rules=$(cat <<'EOF'
id: python-class
message: Collect Python class names
severity: warning
language: Python
rule:
  kind: class_definition
  has:
    field: name
    pattern: $NAME
---
id: typescript-class
message: Collect TypeScript class names
severity: warning
language: TypeScript
rule:
  kind: class_declaration
  has:
    field: name
    pattern: $NAME
---
id: tsx-class
message: Collect TSX class names
severity: warning
language: Tsx
rule:
  kind: class_declaration
  has:
    field: name
    pattern: $NAME
EOF
)

    sg scan --inline-rules "$rules" --json=stream \
        | jq -r '
            select(
                .ruleId != "python-class"
                or ((.charCount.leading? // 0) == 0)
            )
            | .metaVariables.single.NAME.text? as $name
            | select($name != null)
            | [
                $name,
                .file,
                (.range.start.line + 1),
                (.text | split("\n")[0])
            ]
            | @tsv
        '
}

UNIQUE_CLASSES=$(
    collect_matches | sort -t "$TAB" -k1,1 -k2,2 -k3,3n -u
)

printf '%s\n' "$UNIQUE_CLASSES" | awk \
    -F '\t' \
    -v changed_files_from="$CHANGED_FILES_FROM" '
BEGIN {
    prev_name = ""
    prev_file = ""
    current_lines = ""
    output = ""
    class_count = 0
    scope_to_changed = (changed_files_from != "")
    group_has_changed = 0
    repo_root = ENVIRON["PWD"]
    header_printed = 0
    failed = 0

    if (scope_to_changed) {
        while ((getline changed_file < changed_files_from) > 0) {
            changed_file = normalize_file(changed_file)
            if (changed_file != "") {
                changed_files[changed_file] = 1
            }
        }
        close(changed_files_from)
    }
}

function normalize_file(file) {
    if (repo_root != "" && index(file, repo_root "/") == 1) {
        file = substr(file, length(repo_root) + 2)
    }
    sub(/^\.\//, "", file)
    return file
}

function is_alembic_migration(file) {
    if (file ~ /(^|\/)_?alembic_migrations\//) {
        return 1
    }
    if (file ~ /(^|\/)alembic\/versions\//) {
        return 1
    }
    if (file ~ /(^|\/)migrations\/versions\//) {
        return 1
    }
    return 0
}

function is_stub_file(file) {
    if (file ~ /\.pyi$/) {
        return 1
    }
    return 0
}

function flush_class() {
    if (prev_name != "") {
        if (prev_file != "") {
            output = output "  - " prev_file ":" current_lines "\n"
        }
        if (class_count > 1 && (!scope_to_changed || group_has_changed)) {
            if (!header_printed) {
                print "Found duplicate class names:"
                header_printed = 1
            }
            print "- " prev_name " defined in:"
            printf "%s", output
            failed = 1
        }
    }
}

NF >= 4 {
    name = $1
    file = normalize_file($2)
    line = $3

    if (is_alembic_migration(file) || is_stub_file(file)) {
        next
    }

    if (scope_to_changed && !(file in changed_files)) {
        next
    }

    if (name != prev_name) {
        flush_class()
        prev_name = name
        prev_file = file
        current_lines = line
        output = ""
        class_count = 1
        group_has_changed = (file in changed_files)
    } else {
        class_count++
        if (file in changed_files) {
            group_has_changed = 1
        }
        if (file != prev_file) {
            output = output "  - " prev_file ":" current_lines "\n"
            prev_file = file
            current_lines = line
        } else {
            current_lines = current_lines "," line
        }
    }
}

END {
    flush_class()
    if (failed == 0) {
        if (scope_to_changed) {
            print "No duplicate class names found in changed files."
        } else {
            print "No duplicate class names found."
        }
    }
    exit failed
}
'
