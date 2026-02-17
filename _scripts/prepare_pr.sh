#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="dev"
DEFAULT_WEB_URL="http://localhost:5173"
DEV_SERVER_HELPER_REL="_scripts/ensure_dev_servers.sh"

usage() {
  cat <<USAGE
Usage: $0

Environment variables:
  PR_DESCRIPTION        Optional short description for commit/PR title
  AUTO_WEB_SCREENSHOT   Set to 0/false to skip web screenshots
  WEB_URL               Web URL used by screenshot helper
USAGE
}

if [[ $# -ne 0 ]]; then
  echo "Unknown option: $1" >&2
  usage
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: run this script inside a git repository." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required." >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "Error: codex CLI is required for PR copy generation." >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
template_path="${repo_root}/pull_request_template.md"
if [[ ! -f "${template_path}" ]]; then
  echo "Error: missing template file at ${template_path}." >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/remotes/origin/${BASE_BRANCH}"; then
  base_ref="origin/${BASE_BRANCH}"
elif git show-ref --verify --quiet "refs/heads/${BASE_BRANCH}"; then
  base_ref="${BASE_BRANCH}"
else
  echo "Error: cannot find ${BASE_BRANCH} locally or in origin." >&2
  exit 1
fi

status_lines=()
while IFS= read -r line; do
  [[ -n "$line" ]] && status_lines+=("$line")
done < <(
  {
    git diff --name-status "${base_ref}...HEAD"
    git diff --name-status --cached
    git diff --name-status
    git ls-files --others --exclude-standard | sed $'s/^/A\t/'
  } | sort -u
)

if [[ ${#status_lines[@]} -eq 0 ]]; then
  echo "No changed files detected vs ${base_ref} or working tree."
  exit 0
fi

seen_labels=","
labels=()
summary_lines=()
changed_files=()

add_label() {
  local label="$1"
  if [[ "${seen_labels}" != *",${label},"* ]]; then
    labels+=("${label}")
    seen_labels+="${label},"
  fi
}

for line in "${status_lines[@]}"; do
  IFS=$'\t' read -r status path_a path_b <<<"${line}"
  code="${status:0:1}"
  file="${path_a}"
  if [[ "${code}" == "R" || "${code}" == "C" ]]; then
    file="${path_b}"
  fi

  changed_files+=("${file}")

  if [[ "${file}" == */* ]]; then
    label="${file%%/*}"
    if [[ "${label}" == "microservices" ]]; then
      label="api"
    fi
    add_label "${label}"
  else
    add_label "misc"
  fi

  case "${code}" in
    A) summary_lines+=("- Added \`${file}\`") ;;
    M) summary_lines+=("- Updated \`${file}\`") ;;
    D) summary_lines+=("- Removed \`${file}\`") ;;
    R) summary_lines+=("- Renamed \`${path_a}\` to \`${path_b}\`") ;;
    C) summary_lines+=("- Copied \`${path_a}\` to \`${path_b}\`") ;;
    U) summary_lines+=("- Resolved merge conflicts in \`${file}\`") ;;
    *) summary_lines+=("- Changed \`${file}\`") ;;
  esac
done

if [[ ${#labels[@]} -eq 0 ]]; then
  labels=("misc")
fi

prefix="["
for i in "${!labels[@]}"; do
  [[ "$i" -gt 0 ]] && prefix+=", "
  prefix+="${labels[$i]}"
done
prefix+="]"

branch_name="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${branch_name}" == "HEAD" ]]; then
  echo "Error: detached HEAD is not supported." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  user_description="${PR_DESCRIPTION:-}"
  if [[ -z "${user_description}" ]]; then
    clean_branch="${branch_name##*/}"
    if [[ "${clean_branch}" != "dev" && "${clean_branch}" != "main" \
      && "${clean_branch}" != "master" && "${clean_branch}" != "staging" ]];
    then
      user_description="${clean_branch//[-_]/ }"
    else
      user_description="update"
    fi
  fi
  commit_title="${prefix} ${user_description}"
  git add -A
  git commit -m "${commit_title}"
else
  commit_title="$(git log -1 --pretty=%s)"
fi

git push -u origin "${branch_name}"

pr_number="$(gh pr list --base "${BASE_BRANCH}" --head "${branch_name}" \
  --state open --json number --jq '.[0].number')"

if [[ -z "${pr_number}" ]]; then
  created_pr_url="$(gh pr create --base "${BASE_BRANCH}" --head \
    "${branch_name}" --title "${commit_title}" \
    --body "_Draft body. Updating via codex..._")"
  pr_number="$(printf '%s' "${created_pr_url}" | sed -E \
    's#.*/pull/([0-9]+)$#\1#')"
fi

if [[ -z "${pr_number}" || ! "${pr_number}" =~ ^[0-9]+$ ]]; then
  echo "Error: unable to resolve PR number for branch ${branch_name}." >&2
  exit 1
fi

context_file="$(mktemp)"
{
  echo "PREFIX=${prefix}"
  echo "COMMIT_TITLE=${commit_title}"
  echo "BASE_REF=${base_ref}"
  echo "BRANCH=${branch_name}"
  echo "SUMMARY_LINES:"
  printf '%s\n' "${summary_lines[@]}"
  echo "CHANGED_FILES:"
  printf '%s\n' "${changed_files[@]}"
} >"${context_file}"

copy_file="$(mktemp)"
{
  cat <<'PROMPT'
You are writing pull request content.
Use this context:
PROMPT
  cat "${context_file}"
  cat <<'PROMPT'
Read pull_request_template.md and output exactly:
TITLE: <final title including prefix>
BODY_START
<full markdown body based on template>
BODY_END
Rules:
- Keep '# Reasoning for Changes' present but empty.
- Keep summary concise and reflect changed files.
- Keep markdown valid.
PROMPT
} | codex exec - >"${copy_file}"

pr_title="$(sed -n 's/^TITLE: //p' "${copy_file}" | head -n 1)"
pr_body="$(awk '/^BODY_START$/{flag=1;next}/^BODY_END$/{flag=0}flag' \
  "${copy_file}")"

if [[ -z "${pr_title}" || -z "${pr_body}" ]]; then
  echo "Error: codex did not return expected TITLE/BODY format." >&2
  exit 1
fi

gh pr edit "${pr_number}" --title "${pr_title}" --body "${pr_body}"

has_web_change="false"
for label in "${labels[@]}"; do
  if [[ "${label}" == "web-app" ]]; then
    has_web_change="true"
    break
  fi
done

if [[ "${has_web_change}" == "true" ]]; then
  screenshot_opt="$(printf '%s' "${AUTO_WEB_SCREENSHOT:-1}" | tr \
    '[:upper:]' '[:lower:]')"
  if [[ "${screenshot_opt}" != "0" && "${screenshot_opt}" != "false" ]]; then
    helper_path="${repo_root}/${DEV_SERVER_HELPER_REL}"
    if [[ -x "${helper_path}" ]] && command -v mise >/dev/null 2>&1; then
      web_url="${WEB_URL:-${DEFAULT_WEB_URL}}"
      if API_URL="${API_URL:-http://127.0.0.1:8000}" WEB_URL="${web_url}" \
        "${helper_path}" && (cd "${repo_root}" && mise run web:screenshot)
      then
        latest_file="$(find "${repo_root}/_screenshot" -type f \
          \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o \
          -iname '*.webp' -o -iname '*.gif' -o -iname '*.svg' \) \
          -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-)"
        if [[ -n "${latest_file}" ]]; then
          relative_file="${latest_file#${repo_root}/}"
          gh pr comment "${pr_number}" --body "Screenshot: ${relative_file}"
        fi
      fi
    fi
  fi
fi

rm -f "${context_file}" "${copy_file}"

echo "PR #${pr_number} updated successfully."
