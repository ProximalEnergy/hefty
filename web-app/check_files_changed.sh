# List of files that do not require a build
EXCLUDE_PATTERN="README.md|docs/|.github/"

# Check for changes in the current commit
if git diff-tree --no-commit-id --name-only -r HEAD | grep -Ev "$EXCLUDE_PATTERN"; then
  echo "Changes detected that require a build."
else
  echo "No changes detected that require a build. Skipping build."
  exit 0
fi