#!/usr/bin/env bash

set -euo pipefail

branch="dev"
days="7"
since=""
until=""

print_help() {
  cat <<'HELP'
Collect recent git work for downstream categorization.

Usage:
  summarize_dev_history.sh [--branch <ref>] [--days <n>]
                         [--since <git-date>] [--until <git-date>]

Options:
  --branch <ref>     Branch/ref to summarize (default: dev)
  --days <n>         Look back N days (default: 7)
  --since <date>     Explicit git --since date (overrides --days)
  --until <date>     Optional git --until date
  --help             Show this help message

Examples:
  summarize_dev_history.sh
  summarize_dev_history.sh --days 14
  summarize_dev_history.sh --since "2026-01-01" --until "2026-01-31"
  summarize_dev_history.sh --branch origin/dev --days 30
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      branch="${2:-}"
      shift 2
      ;;
    --days)
      days="${2:-}"
      shift 2
      ;;
    --since)
      since="${2:-}"
      shift 2
      ;;
    --until)
      until="${2:-}"
      shift 2
      ;;
    --help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_help >&2
      exit 1
      ;;
  esac
done

if ! git rev-parse --verify "$branch" >/dev/null 2>&1; then
  if [[ "$branch" == "dev" ]] \
    && git rev-parse --verify origin/dev >/dev/null 2>&1; then
    branch="origin/dev"
  else
    echo "Could not resolve branch/ref '$branch'." >&2
    echo "Try using --branch origin/dev if dev is only on remote." >&2
    exit 1
  fi
fi

if [[ -z "$since" ]]; then
  since="${days} days ago"
fi

log_cmd=(
  git log "$branch" "--since=$since"
  --pretty=format:'%H%x1f%s%x1f%b%x1e'
)
if [[ -n "$until" ]]; then
  log_cmd+=("--until=$until")
fi
log_output="$("${log_cmd[@]}")"

if [[ -z "$log_output" ]]; then
  echo "# Dev history summary"
  echo
  echo "No commits found on '$branch' since '$since'."
  exit 0
fi

print_header() {
  echo "# Dev history summary"
  echo
  printf -- '- Branch: `%s`\n' "$branch"
  printf -- '- Since: `%s`\n' "$since"
  if [[ -n "$until" ]]; then
    printf -- '- Until: `%s`\n' "$until"
  fi
  echo
}

build_commit_context() {
  local context=""

  while IFS= read -r -d $'\x1e' record; do
    [[ -z "$record" ]] && continue

    local hash rest subject body short_hash clean_body
    hash="${record%%$'\x1f'*}"
    rest="${record#*$'\x1f'}"
    subject="${rest%%$'\x1f'*}"
    body="${rest#*$'\x1f'}"
    hash="${hash//$'\n'/}"
    hash="${hash//$'\r'/}"
    subject="${subject%%$'\n'*}"
    subject="${subject//$'\r'/}"
    body="${body//$'\r'/ }"
    short_hash="${hash:0:8}"
    clean_body="$(echo "$body" | tr '\n' ' ' | tr '\r' ' ')"
    clean_body="$(echo "$clean_body" | tr -s ' ')"
    context+="- ${short_hash} | ${subject}"
    if [[ -n "${clean_body// }" ]]; then
      context+=" | ${clean_body}"
    fi
    context+=$'\n'
  done < <(printf %s "$log_output")

  printf '%s' "$context"
}

print_header
echo "## Commit history"
echo
printf '%s\n' "$(build_commit_context)"
