#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="dev"
REPO_ROOT=""
TEMPLATE_PATH=""
DEFAULT_WEB_URL="http://127.0.0.1:5173"
DEV_SERVER_HELPER_REL=".agents/skills/dev-pr-screenshot/scripts/\
ensure_dev_servers.sh"
PLAYWRIGHT_WRAPPER_DEFAULT="$HOME/.codex/skills/playwright/scripts/\
playwright_cli.sh"

usage() {
  cat <<USAGE
Usage: $0
Note: Set PR_DESCRIPTION environment variable to provide a custom description.
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

REPO_ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH="${REPO_ROOT}/pull_request_template.md"
if [[ ! -f "${TEMPLATE_PATH}" ]]; then
  echo "Error: missing template file at ${TEMPLATE_PATH}." >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/remotes/origin/${BASE_BRANCH}"; then
  BASE_REF="origin/${BASE_BRANCH}"
elif git show-ref --verify --quiet "refs/heads/${BASE_BRANCH}"; then
  BASE_REF="${BASE_BRANCH}"
else
  echo "Error: cannot find ${BASE_BRANCH} locally or as origin/${BASE_BRANCH}." >&2
  exit 1
fi

status_lines=()
while IFS= read -r line; do
  [[ -n "$line" ]] && status_lines+=("$line")
done < <(
  {
    git diff --name-status "${BASE_REF}...HEAD"
    git diff --name-status --cached
    git diff --name-status
    git ls-files --others --exclude-standard | sed $'s/^/A\t/'
  } | sort -u
)

if [[ ${#status_lines[@]} -eq 0 ]]; then
  echo "No changed files detected vs ${BASE_REF} or working tree."
  exit 0
fi

seen=""
labels=()
summary_lines=()
summary_files=()
summary_texts=()
summary_priorities=()
media_lines=()
image_ext_re='(png|jpg|jpeg|gif|webp|svg)$'
video_ext_re='(mp4|mov|webm|m4v)$'
seen_media=""

add_label() {
  local label="$1"
  if [[ ",${seen}," != *",${label},"* ]]; then
    labels+=("${label}")
    seen="${seen},${label}"
  fi
}

summary_priority() {
  local code="$1"
  case "${code}" in
    A|D|R|C)
      echo "3"
      ;;
    M|U)
      echo "2"
      ;;
    *)
      echo "1"
      ;;
  esac
}

upsert_summary() {
  local file="$1"
  local text="$2"
  local priority="$3"
  local i
  for i in "${!summary_files[@]}"; do
    if [[ "${summary_files[$i]}" == "${file}" ]]; then
      if (( priority >= summary_priorities[$i] )); then
        summary_texts[$i]="${text}"
        summary_priorities[$i]="${priority}"
      fi
      return
    fi
  done
  summary_files+=("${file}")
  summary_texts+=("${text}")
  summary_priorities+=("${priority}")
}

for line in "${status_lines[@]}"; do
  IFS=$'\t' read -r status path_a path_b <<<"${line}"
  code="${status:0:1}"
  file="${path_a}"
  if [[ "${code}" == "R" || "${code}" == "C" ]]; then
    file="${path_b}"
  fi

  if [[ "$file" == *"/"* ]]; then
    label="${file%%/*}"
    # Special case: map microservices to api as conceptually related here.
    if [[ "$label" == "microservices" ]]; then
      label="api"
    fi
    add_label "$label"
  else
    add_label "misc"
  fi

  summary_text=""
  case "${code}" in
    A)
      summary_text="- Added \`${file}\`"
      ;;
    M)
      summary_text="- Updated \`${file}\`"
      ;;
    D)
      summary_text="- Removed \`${file}\`"
      ;;
    R)
      summary_text="- Renamed \`${path_a}\` to \`${path_b}\`"
      ;;
    C)
      summary_text="- Copied \`${path_a}\` to \`${path_b}\`"
      ;;
    U)
      summary_text="- Resolved merge conflicts in \`${file}\`"
      ;;
    *)
      summary_text="- Changed \`${file}\`"
      ;;
  esac
  priority="$(summary_priority "${code}")"
  upsert_summary "${file}" "${summary_text}" "${priority}"

  lowered="$(printf "%s" "${file}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${lowered}" =~ \.${image_ext_re} ]]; then
    if [[ ",${seen_media}," != *",${file},"* ]]; then
      media_lines+=("- ![${file}](${file})")
      seen_media="${seen_media},${file}"
    fi
  elif [[ "${lowered}" =~ \.${video_ext_re} ]]; then
    if [[ ",${seen_media}," != *",${file},"* ]]; then
      media_lines+=("- [${file}](${file})")
      seen_media="${seen_media},${file}"
    fi
  fi
done

summary_lines=("${summary_texts[@]}")

if [[ ${#labels[@]} -eq 0 ]]; then
  labels=("root")
fi

prefix="["
for i in "${!labels[@]}"; do
  if [[ "$i" -gt 0 ]]; then
    prefix+=", "
  fi
  prefix+="${labels[$i]}"
done
prefix+="]"

join_lines() {
  local output=""
  local entry
  for entry in "$@"; do
    if [[ -n "${output}" ]]; then
      output+=$'\n'
    fi
    output+="${entry}"
  done
  printf "%s" "${output}"
}

replace_section() {
  local input="$1"
  local header="$2"
  local content="$3"
  local content_file
  content_file="$(mktemp)"
  printf "%s\n" "${content}" >"${content_file}"
  awk -v header="${header}" -v content_file="${content_file}" '
function print_content() {
  while ((getline line < content_file) > 0) {
    print line
  }
  close(content_file)
}
BEGIN {
  in_section = 0
  replaced = 0
}
{
  if ($0 == header) {
    print $0
    print ""
    print_content()
    in_section = 1
    replaced = 1
    next
  }
  if (in_section && /^## /) {
    in_section = 0
    print $0
    next
  }
  if (!in_section) {
    print $0
  }
}
END {
  if (!replaced) {
    if (NR > 0) {
      print ""
    }
    print header
    print ""
    print_content()
  }
}' <<<"${input}"
  rm -f "${content_file}"
}

has_label() {
  local target="$1"
  local label
  for label in "${labels[@]}"; do
    if [[ "${label}" == "${target}" ]]; then
      return 0
    fi
  done
  return 1
}

capture_web_screenshot() {
  local screenshot_opt
  screenshot_opt="$(printf "%s" "${AUTO_WEB_SCREENSHOT:-1}" | tr \
    '[:upper:]' '[:lower:]')"
  if [[ "${screenshot_opt}" == "0" || "${screenshot_opt}" == "false" ]]; then
    echo "Skipping Playwright capture: AUTO_WEB_SCREENSHOT=${AUTO_WEB_SCREENSHOT:-1}"
    return 0
  fi

  local helper_path="${REPO_ROOT}/${DEV_SERVER_HELPER_REL}"
  if [[ ! -x "${helper_path}" ]]; then
    echo "Skipping Playwright capture: missing helper at ${helper_path}"
    return 0
  fi

  local pwcli_path="${PWCLI:-${PLAYWRIGHT_WRAPPER_DEFAULT}}"
  if ! command -v npx >/dev/null 2>&1 || [[ ! -x "${pwcli_path}" ]]; then
    echo "Skipping Playwright capture: npx or wrapper script unavailable."
    return 0
  fi

  local web_url="${WEB_URL:-${DEFAULT_WEB_URL}}"
  if ! API_URL="${API_URL:-http://127.0.0.1:8000}" WEB_URL="${web_url}" \
    "${helper_path}"; then
    echo "Skipping Playwright capture: unable to start API/web services."
    return 0
  fi

  local shot_dir="${REPO_ROOT}/artifacts/pr-screenshots"
  mkdir -p "${shot_dir}"
  local marker
  marker="$(mktemp)"
  touch "${marker}"
  local session="dev-pr-screenshot"

  pushd "${shot_dir}" >/dev/null
  if "${pwcli_path}" --session "${session}" open "${web_url}" >/dev/null 2>&1 \
    && "${pwcli_path}" --session "${session}" snapshot >/dev/null 2>&1 \
    && "${pwcli_path}" --session "${session}" screenshot >/dev/null 2>&1; then
    :
  else
    echo "Playwright capture command failed. Continuing without screenshot."
  fi
  "${pwcli_path}" --session "${session}" close >/dev/null 2>&1 || true
  popd >/dev/null

  local new_file=""
  new_file="$(find "${shot_dir}" -maxdepth 1 -type f \
    \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \
    \) -newer "${marker}" | sort | head -n 1)"
  rm -f "${marker}"

  if [[ -n "${new_file}" ]]; then
    local relative_file="${new_file#${REPO_ROOT}/}"
    media_lines+=("- ![${relative_file}](${relative_file})")
    echo "Captured Playwright screenshot: ${relative_file}"
  else
    echo "No new Playwright screenshot detected."
  fi
}

if has_label "web-app"; then
  capture_web_screenshot
fi

summary_content="$(join_lines "${summary_lines[@]}")"
template="$(cat "${TEMPLATE_PATH}")"
template="$(
  replace_section "${template}" "## Summary of Changes" "${summary_content}"
)"
if [[ ${#media_lines[@]} -gt 0 ]]; then
  media_content="$(join_lines "${media_lines[@]}")"
  template="$(
    replace_section "${template}" "## Screenshots and Videos" "${media_content}"
  )"
fi

echo "Detected base: ${BASE_REF}"
echo "Suggested title prefix: ${prefix}"
echo
echo "Suggested title format: ${prefix} short description"
if [[ ${#media_lines[@]} -gt 0 ]]; then
  echo "Detected media files for Screenshots and Videos: ${#media_lines[@]}"
else
  echo "No media files detected for Screenshots and Videos."
fi
echo
echo "PR body template:"
echo "-----------------"
echo "${template}"
echo "-----------------"

PR_TITLE=""
branch_name="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${branch_name}" == "HEAD" ]]; then
  echo "Error: detached HEAD is not supported." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "You have uncommitted changes."
  user_description="${PR_DESCRIPTION:-}"

  # Prompt for description if PR_DESCRIPTION is not set and stdin is a terminal
  if [[ -z "${user_description}" && -t 0 ]]; then
    printf "Enter a short description for the commit/PR [leave empty for default]: "
    read -r user_description
  fi

  if [[ -z "${user_description}" ]]; then
    # Fallback: use branch name (minus prefix) if it's not a common branch name
    clean_branch="${branch_name##*/}"
    if [[ "${clean_branch}" != "dev" && "${clean_branch}" != "main" \
      && "${clean_branch}" != "master" \
      && "${clean_branch}" != "staging" ]]; then
      user_description="${clean_branch//[-_]/ }"
    else
      user_description="update"
    fi
  fi

  DEFAULT_COMMIT_MESSAGE="${prefix} ${user_description}"
  git add -A
  git commit -m "${DEFAULT_COMMIT_MESSAGE}"
  PR_TITLE="${DEFAULT_COMMIT_MESSAGE}"
else
  echo "No uncommitted changes; skipping commit step."
  # If no commit was made but PR_DESCRIPTION was provided, use it for the PR title
  if [[ -n "${PR_DESCRIPTION:-}" ]]; then
     PR_TITLE="${prefix} ${PR_DESCRIPTION}"
  fi
fi

if [[ -z "${PR_TITLE}" ]]; then
  PR_TITLE="$(git log -1 --pretty=%s)"
fi
if [[ -z "${PR_TITLE}" ]]; then
  PR_TITLE="${DEFAULT_COMMIT_MESSAGE}"
fi

git push -u origin "${branch_name}"
gh pr create --base "${BASE_BRANCH}" --title "${PR_TITLE}" \
  --body "${template}"
