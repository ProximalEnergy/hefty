#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="dev"
DEFAULT_WEB_URL="http://localhost:5173"
DEV_SERVER_HELPER_REL="_scripts/ensure_dev_servers.sh"
PR_ASSETS_RELEASE_TAG="${PR_ASSETS_RELEASE_TAG:-pr-assets}"

usage() {
  cat <<USAGE
Usage: $0

Environment variables:
  PR_DESCRIPTION        Optional short description for commit/PR title
  AUTO_WEB_SCREENSHOT   Set to 0/false to skip web screenshots
  WEB_URL               Web URL used by screenshot helper
  PR_ASSETS_RELEASE_TAG Release tag used for PR screenshot assets
  PR_DIFF_CONTEXT_LINES Max diff lines sent to codex (default: 1200)
USAGE
}

cleanup_closed_pr_assets() {
  local release_tag="$1"
  local open_pr_numbers
  local asset_names
  local asset_name
  local asset_pr

  if ! open_pr_numbers="$(gh pr list --state open --limit 500 \
    --json number --jq '.[].number' 2>/dev/null)"
  then
    return 0
  fi

  if ! asset_names="$(gh release view "${release_tag}" --json assets \
    --jq '.assets[].name' 2>/dev/null)"
  then
    return 0
  fi

  while IFS= read -r asset_name; do
    [[ -z "${asset_name}" ]] && continue
    if [[ "${asset_name}" =~ ^pr-([0-9]+)- ]]; then
      asset_pr="${BASH_REMATCH[1]}"
      if ! grep -Fxq "${asset_pr}" <<<"${open_pr_numbers}"; then
        gh release delete-asset "${release_tag}" "${asset_name}" \
          --yes >/dev/null 2>&1 || true
      fi
    fi
  done <<<"${asset_names}"
}

update_pr_screenshots_section() {
  local pr_number="$1"
  local pr_title="$2"
  local screenshot_md="$3"
  local current_body
  local updated_body

  current_body="$(gh pr view "${pr_number}" --json body --jq '.body')"

  updated_body="$(awk -v block="${screenshot_md}" '
    BEGIN {
      in_section = 0
      replaced = 0
    }
    /^##[[:space:]]+Screenshots and Videos[[:space:]]*$/ {
      print
      print ""
      print block
      in_section = 1
      replaced = 1
      next
    }
    in_section && /^##[[:space:]]+/ {
      in_section = 0
    }
    !in_section {
      print
    }
    END {
      if (!replaced) {
        if (NR > 0) {
          print ""
        }
        print "## Screenshots and Videos"
        print ""
        print block
      }
    }
  ' <<<"${current_body}")"

  gh pr edit "${pr_number}" --title "${pr_title}" --body "${updated_body}" \
    >/dev/null 2>&1 || true
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

diff_context_lines="${PR_DIFF_CONTEXT_LINES:-1200}"
if [[ ! "${diff_context_lines}" =~ ^[0-9]+$ ]] || \
  [[ "${diff_context_lines}" -le 0 ]]; then
  diff_context_lines=1200
fi

diff_file="$(mktemp)"
git diff --no-color --find-renames --unified=1 "${base_ref}...HEAD" \
  >"${diff_file}"
diff_total_lines="$(wc -l <"${diff_file}" | tr -d ' ')"

commit_log="$(git log --reverse --pretty='- %h %s' "${base_ref}..HEAD")"
if [[ -z "${commit_log}" ]]; then
  commit_log="- No commits between ${base_ref} and HEAD."
fi

diff_stat="$(git diff --stat --find-renames "${base_ref}...HEAD")"
if [[ -z "${diff_stat}" ]]; then
  diff_stat="- No diff stat available."
fi

context_file="$(mktemp)"
{
  echo "PREFIX=${prefix}"
  echo "COMMIT_TITLE=${commit_title}"
  echo "BASE_REF=${base_ref}"
  echo "BRANCH=${branch_name}"
  echo "FILE_STATUS_LINES:"
  printf '%s\n' "${status_lines[@]}"
  echo "COMMIT_LOG:"
  printf '%s\n' "${commit_log}"
  echo "DIFF_STAT:"
  printf '%s\n' "${diff_stat}"
  echo "CHANGED_FILES:"
  printf '%s\n' "${changed_files[@]}"
  echo "DIFF_EXCERPT:"
  sed -n "1,${diff_context_lines}p" "${diff_file}"
  if [[ "${diff_total_lines}" -gt "${diff_context_lines}" ]]; then
    echo
    echo "[Diff truncated. Showing first ${diff_context_lines} of "\
"${diff_total_lines} lines.]"
  fi
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
- In '## Summary of Changes', explain application behavior changes in plain
  English.
- Focus on user-visible effects, API contract changes, and operational impact.
- Do not provide a file-by-file list unless needed for clarity.
- If context is incomplete, state assumptions briefly and avoid fabricated
  details.
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
        latest_file="$(
          find "${repo_root}/_screenshot" -type f \
            \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o \
            -iname '*.webp' -o -iname '*.gif' -o -iname '*.svg' \) \
            -print0 | while IFS= read -r -d '' file; do
              mtime="$(stat -f '%m' "${file}")" || continue
              printf '%s\t%s\n' "${mtime}" "${file#${repo_root}/}"
            done | sort -nr | head -n 1 | cut -f2-
        )"
        if [[ -n "${latest_file}" ]]; then
          asset_name="pr-${pr_number}-$(basename "${latest_file}")"
          screenshot_path="${repo_root}/${latest_file}"
          tmp_asset_dir="$(mktemp -d)"
          tmp_asset_path="${tmp_asset_dir}/${asset_name}"
          release_tag="${PR_ASSETS_RELEASE_TAG}"
          release_ready="false"
          cp "${screenshot_path}" "${tmp_asset_path}"
          if gh release view "${release_tag}" >/dev/null 2>&1; then
            release_ready="true"
          elif gh release create "${release_tag}" \
            --title "PR Assets" \
            --notes "Automated PR screenshot assets." >/dev/null 2>&1
          then
            release_ready="true"
          elif gh release view "${release_tag}" >/dev/null 2>&1; then
            release_ready="true"
          fi

          if [[ "${release_ready}" == "true" ]] && gh release upload \
            "${release_tag}" "${tmp_asset_path}" --clobber \
            >/dev/null 2>&1
          then
            cleanup_closed_pr_assets "${release_tag}"
            image_url="$(gh release view "${release_tag}" --json assets --jq \
              ".assets[] | select(.name == \"${asset_name}\") | .url" \
              2>/dev/null || true)"
            if [[ -n "${image_url}" ]]; then
              image_body="![${asset_name}](${image_url})"
              update_pr_screenshots_section "${pr_number}" "${pr_title}" \
                "${image_body}"
            else
              image_body="Screenshot: ${latest_file}"
              update_pr_screenshots_section "${pr_number}" "${pr_title}" \
                "${image_body}"
            fi
          else
            image_body="Screenshot: ${latest_file}"
            update_pr_screenshots_section "${pr_number}" "${pr_title}" \
              "${image_body}"
          fi
          rm -rf "${tmp_asset_dir}"
        fi
      fi
    fi
  fi
fi

rm -f "${context_file}" "${copy_file}" "${diff_file}"

pr_url="$(gh pr view "${pr_number}" --json url --jq '.url' 2>/dev/null || \
  true)"

echo "PR #${pr_number} updated successfully."
if [[ -n "${pr_url}" ]]; then
  printf 'PR URL: %s\n' "${pr_url}"
  printf 'Open PR: \033]8;;%s\033\\%s\033]8;;\033\\\n' \
    "${pr_url}" "${pr_url}"
fi
