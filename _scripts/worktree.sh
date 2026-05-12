#!/bin/bash
set -e

# =============================================================================
# Git Worktree Setup Script
# Creates a new worktree with environment files and opens in editor.
# Without --existing: creates a new branch. With --existing: fetches, resolves
# the branch name (local or origin/<branch>), and checks out that ref.
#
# Usage: ./worktree.sh <folder-name> <branch-name> [editor] [--existing]
# =============================================================================

FOLDER_NAME="${1:?Usage: mise run worktree <folder-name> <branch-name> [-e editor] [-x]}"
BRANCH_NAME="${2:?Usage: mise run worktree <folder-name> <branch-name> [-e editor] [-x]}"
USE_EXISTING=0
EDITOR_CHOICE=""
for arg in "${3:-}" "${4:-}"; do
    if [[ "$arg" == "--existing" ]]; then
        USE_EXISTING=1
    elif [[ "$arg" == "cursor" || "$arg" == "zed" ]]; then
        EDITOR_CHOICE="$arg"
    fi
done

# Paths
CURRENT_DIR="$(pwd)"
PARENT_DIR="$(dirname "$CURRENT_DIR")"
NEW_WORKTREE="$PARENT_DIR/$FOLDER_NAME"
OVERLAY_DIR="$HOME/.devconfig/mono"

# =============================================================================
# FILES TO COPY (edit this list as needed)
# =============================================================================
FILES_TO_COPY=(
    ".vscode/launch.json"
    "api/.env"
    "core/.env"
    "web-app/.env"
    "kpi/.env"
)

echo "Creating worktree at: $NEW_WORKTREE"
echo "Branch: $BRANCH_NAME"

# Create the worktree (new branch or existing)
if [[ "$USE_EXISTING" -eq 1 ]]; then
    echo "Fetching..."
    git fetch
    RESOLVED_REF=""
    if git rev-parse --verify "$BRANCH_NAME" &>/dev/null; then
        RESOLVED_REF="$BRANCH_NAME"
    elif git rev-parse --verify "origin/$BRANCH_NAME" &>/dev/null; then
        RESOLVED_REF="origin/$BRANCH_NAME"
    else
        echo "Branch not found: $BRANCH_NAME (tried local and origin/$BRANCH_NAME)"
        exit 1
    fi
    if [[ "$RESOLVED_REF" == "$BRANCH_NAME" ]]; then
        git worktree add "$NEW_WORKTREE" "$BRANCH_NAME"
    else
        git worktree add -b "$BRANCH_NAME" "$NEW_WORKTREE" "origin/$BRANCH_NAME"
    fi
else
    git worktree add -b "$BRANCH_NAME" "$NEW_WORKTREE"
fi

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

# Overlay local devconfig files if present
if [[ -d "$OVERLAY_DIR" ]]; then
    echo "Applying devconfig overlay from: $OVERLAY_DIR"
    cp -a "$OVERLAY_DIR"/. "$NEW_WORKTREE"/
    echo "  Overlay applied"
else
    echo "Devconfig overlay not found, skipping: $OVERLAY_DIR"
fi

# Copy the root Cursor workspace using the new worktree title
if [[ -f "$CURRENT_DIR/mono.code-workspace" ]]; then
    WORKSPACE_FILE="$(basename "$FOLDER_NAME").code-workspace"
    cp "$CURRENT_DIR/mono.code-workspace" "$NEW_WORKTREE/$WORKSPACE_FILE"
    echo "Copied workspace file: $WORKSPACE_FILE"
else
    echo "Workspace file not found, skipping: mono.code-workspace"
fi

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
