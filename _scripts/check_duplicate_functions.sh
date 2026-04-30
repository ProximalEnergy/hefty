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
id: python-function
message: Collect Python function names
severity: warning
language: Python
rule:
  kind: function_definition
  has:
    field: name
    pattern: $NAME
---
id: typescript-function
message: Collect TypeScript function names
severity: warning
language: TypeScript
rule:
  any:
    - pattern: 'function $NAME($$$A) { $$$B }'
    - pattern: 'async function $NAME($$$A) { $$$B }'
    - pattern: 'const $NAME = ($$$A) => { $$$B }'
    - pattern: 'const $NAME = async ($$$A) => { $$$B }'
---
id: tsx-function
message: Collect TSX function names
severity: warning
language: Tsx
rule:
  any:
    - pattern: 'function $NAME($$$A) { $$$B }'
    - pattern: 'async function $NAME($$$A) { $$$B }'
    - pattern: 'const $NAME = ($$$A) => { $$$B }'
    - pattern: 'const $NAME = async ($$$A) => { $$$B }'
EOF
)

    sg scan --inline-rules "$rules" --json=stream \
        | jq -r '
            .metaVariables.single.NAME.text? as $name
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

UNIQUE_FUNCS=$(
    collect_matches | sort -t "$TAB" -k1,1 -k2,2 -k3,3n -u
)

printf '%s\n' "$UNIQUE_FUNCS" | awk \
    -F '\t' \
    -v changed_files_from="$CHANGED_FILES_FROM" '
BEGIN {
    prev_name = ""
    prev_file = ""
    current_lines = ""
    output = ""
    func_count = 0
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

function is_allowed_duplicate(name, signature) {
    if (name == "render") {
        if (signature ~ /^def render\(self\)([[:space:]]*->[^:]+)?:$/) {
            return 1
        }
    }
    return 0
}

function flush_func() {
    if (prev_name != "") {
        if (prev_file != "") {
            output = output "  - " prev_file ":" current_lines "\n"
        }
        if (func_count > 1 && (!scope_to_changed || group_has_changed)) {
            if (!header_printed) {
                print "Found duplicate function names:"
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
    signature = $4

    if (is_alembic_migration(file)) {
        next
    }

    if (name ~ /^__.*__$/ || name == "lambda_handler" || name == "health_check") {
        next
    }

    if (is_stub_file(file) || is_allowed_duplicate(name, signature)) {
        next
    }

    if (scope_to_changed && !(file in changed_files)) {
        next
    }

    if (name != prev_name) {
        flush_func()
        prev_name = name
        prev_file = file
        current_lines = line
        output = ""
        func_count = 1
        group_has_changed = (file in changed_files)
    } else {
        func_count++
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
    flush_func()
    if (failed == 0) {
        if (scope_to_changed) {
            print "No duplicate function names found in changed files."
        } else {
            print "No duplicate function names found."
        }
    }
    exit failed
}
'
