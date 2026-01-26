#!/bin/bash
set -e

# =============================================================================
# Git Worktree Setup Script
# Creates a new worktree with environment files and opens in editor
#
# Usage: ./worktree.sh <folder-name> <branch-name> [editor]
# =============================================================================

FOLDER_NAME="${1:?Usage: mise run worktree <folder-name> <branch-name> [-e editor]}"
BRANCH_NAME="${2:?Usage: mise run worktree <folder-name> <branch-name> [-e editor]}"
EDITOR_CHOICE="${3:-}"

# Paths
CURRENT_DIR="$(pwd)"
PARENT_DIR="$(dirname "$CURRENT_DIR")"
NEW_WORKTREE="$PARENT_DIR/$FOLDER_NAME"

# =============================================================================
# FILES TO COPY (edit this list as needed)
# =============================================================================
FILES_TO_COPY=(
    ".vscode/launch.json"
    "api/.env"
    "core/.env"
    "web-app/.env"
)

echo "Creating worktree at: $NEW_WORKTREE"
echo "Branch: $BRANCH_NAME"

# Create the worktree with new branch
git worktree add -b "$BRANCH_NAME" "$NEW_WORKTREE"

# Copy environment files
echo "Copying environment files..."
for file in "${FILES_TO_COPY[@]}"; do
    if [[ -f "$CURRENT_DIR/$file" ]]; then
        mkdir -p "$(dirname "$NEW_WORKTREE/$file")"
        cp "$CURRENT_DIR/$file" "$NEW_WORKTREE/$file"
        echo "  Copied: $file"
    else
        echo "  Skipped (not found): $file"
    fi
done

# Trust mise config files in new worktree
echo "Trusting mise config files..."
cd "$NEW_WORKTREE"
mise trust
mise trust api/.mise.toml
mise trust core/.mise.toml

# Run sync-deps in new worktree
echo "Setting up environments (mise run sync-deps)..."
mise run sync-deps

# Open in editor (if specified)
if [[ -n "$EDITOR_CHOICE" ]]; then
    echo "Opening in $EDITOR_CHOICE..."
    case "$EDITOR_CHOICE" in
        cursor)
            cursor "$NEW_WORKTREE"
            ;;
        zed)
            zed "$NEW_WORKTREE"
            ;;
        *)
            echo "Unknown editor: $EDITOR_CHOICE (supported: cursor, zed)"
            ;;
    esac
fi

echo ""
echo "Worktree ready at: $NEW_WORKTREE"
echo "Branch: $BRANCH_NAME"
