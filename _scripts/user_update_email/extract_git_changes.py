#!/usr/bin/env python3
"""Script to extract git changes from main branch merges and generate a prompt for Cursor AI.

This script:
1. Extracts merge commits from main branch since a specified date or commit
2. Formats the changes into a structured format
3. Generates a prompt file that can be used with Cursor AI to create platform update emails

Usage:
    python extract_git_changes.py [--since DATE] [--since-commit COMMIT] [--output output.txt]
    
Examples:
    python extract_git_changes.py --since "2025-10-01"
    python extract_git_changes.py --since-commit abc123
    python extract_git_changes.py --since "2025-10-01" --output changes_prompt.txt
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_git_command(cmd: list[str]) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(cmd)}")
        logger.error(f"Error: {e.stderr}")
        raise


def get_merge_commits_since(since: Optional[str] = None, since_commit: Optional[str] = None) -> list[dict]:
    """Get merge commits from main branch since a date or commit.
    
    Args:
        since: Date string (e.g., "2025-10-01")
        since_commit: Commit hash to start from
        
    Returns:
        List of dictionaries with commit information
    """
    # Ensure we're on main and up to date
    logger.info("Fetching latest changes from origin...")
    run_git_command(["fetch", "origin", "main"])
    
    # Determine the starting point
    if since_commit:
        start_point = since_commit
    elif since:
        # Find the commit at or before the date
        try:
            start_point = run_git_command([
                "rev-list", "-n", "1", "--before", since, "origin/main"
            ])
            if not start_point:
                logger.warning(f"No commits found before {since}, using HEAD")
                start_point = "HEAD"
        except Exception:
            logger.warning(f"Could not find commit for date {since}, using HEAD")
            start_point = "HEAD"
    else:
        # Default: last 3 months
        from datetime import timedelta
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        start_point = run_git_command([
            "rev-list", "-n", "1", "--before", three_months_ago, "origin/main"
        ]) or "HEAD"
    
    logger.info(f"Extracting merge commits since {start_point}...")
    
    # Get merge commits (commits with more than one parent)
    # Format: hash|author|date|subject|body
    format_str = "%H|%an|%ad|%s|%b"
    cmd = [
        "log",
        f"{start_point}..origin/main",
        "--merges",
        "--pretty=format:" + format_str,
        "--date=short",
    ]
    
    output = run_git_command(cmd)
    
    if not output:
        logger.warning("No merge commits found")
        return []
    
    commits = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        
        parts = line.split("|", 4)
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "subject": parts[3],
                "body": parts[4] if len(parts) > 4 else "",
            })
    
    logger.info(f"Found {len(commits)} merge commits")
    return commits


def get_pr_number_from_commit(commit_hash: str) -> Optional[str]:
    """Try to extract PR number from commit message or merge commit."""
    try:
        # Get the full commit message
        message = run_git_command(["log", "-1", "--pretty=%B", commit_hash])
        
        # Look for PR number patterns: #123, PR #123, Merge pull request #123
        import re
        patterns = [
            r"#(\d+)",
            r"PR\s*#(\d+)",
            r"pull request #(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass
    
    return None


def format_commits_for_prompt(commits: list[dict]) -> str:
    """Format commits into a structured prompt for Cursor AI."""
    if not commits:
        return "No merge commits found in the specified time range."
    
    lines = [
        "# Git Changes Summary",
        "",
        f"Found {len(commits)} merge commits since the last update:",
        "",
    ]
    
    for i, commit in enumerate(commits, 1):
        pr_num = get_pr_number_from_commit(commit["hash"])
        pr_info = f" (PR #{pr_num})" if pr_num else ""
        
        lines.extend([
            f"## {i}. {commit['subject']}{pr_info}",
            f"**Date:** {commit['date']}",
            f"**Author:** {commit['author']}",
            f"**Commit:** {commit['hash'][:8]}",
        ])
        
        if commit['body']:
            # Clean up the body (remove extra whitespace, merge markers)
            body = commit['body'].strip()
            # Remove common merge commit artifacts
            body = body.replace("Merge branch", "").strip()
            if body and not body.startswith("Co-authored-by"):
                lines.append(f"**Details:** {body}")
        
        lines.append("")
    
    return "\n".join(lines)


def generate_cursor_prompt(commits: list[dict], output_file: str = "cursor_prompt.txt"):
    """Generate a prompt file for Cursor AI to create platform update emails."""
    changes_summary = format_commits_for_prompt(commits)
    
    prompt = f"""# Platform Update Email Generation Prompt

Our Proximal platform is a Performance Analytics and Asset Management platform that helps users get the best out of their utility scale solar and storage projects.
Use the following git changes to create a professional platform update email for our users - write it as if you're an expert in the solar industry, and also your audience are experts as well.

## Git Changes

{changes_summary}

## Instructions

Please create a platform update email based on the git changes above. The email should:

1. **Review PRs**: For each PR number listed, use GitHub CLI (`gh pr view <PR_NUMBER>`) or GitHub API to fetch the PR title and description. Many PRs have detailed Greptile summaries that explain the changes. Focus on user-facing features and improvements.

2. **Be user-friendly**: Focus on features and improvements that users will notice and benefit from
3. **Be organized**: Group changes into logical categories:
   - 🆕 New Features
   - 🎨 User Interface Improvements
   - 🐛 Bug Fixes
   - 🔧 Technical Improvements
   - 📚 Documentation
4. **Be concise**: Don't overwhelm users with too much technical detail
5. **Highlight value**: Emphasize how changes improve the user experience
6. **Use the email template**: Reference `email_template.html` for consistent styling

## Email Template

The email template is located at `email_template.html`. Use it as a reference for:
- HTML structure and styling
- Section organization
- Tone and formatting

## Output Format

Generate the email in both:
1. **HTML format** (for email clients) - save as `platform_update_[DATE].html`
2. **Markdown format** (for documentation) - save as `platform_update_[DATE].md`

Replace [DATE_PLACEHOLDER] with the current date (e.g., "December 2025").

## Notes

- Focus on user-facing changes rather than internal technical improvements
- Group similar changes together
- Use clear, non-technical language
- Include "Getting Started" section if there are new features that need explanation
- Many PRs are automated merges from staging to main - focus on the actual feature PRs that were merged into dev/staging
- PRs with Greptile summaries contain detailed explanations of changes that are very helpful for understanding what was actually changed
"""
    
    output_path = Path(output_file)
    output_path.write_text(prompt, encoding="utf-8")
    logger.info(f"Generated prompt file: {output_path}")
    
    return prompt


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract git changes and generate Cursor AI prompt for platform update emails"
    )
    parser.add_argument(
        "--since",
        help="Start date (YYYY-MM-DD format, e.g., 2025-10-01)",
    )
    parser.add_argument(
        "--since-commit",
        help="Start from this commit hash",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="cursor_prompt.txt",
        help="Output prompt file path (default: cursor_prompt.txt)",
    )
    
    args = parser.parse_args()
    
    if args.since and args.since_commit:
        logger.error("Cannot specify both --since and --since-commit")
        sys.exit(1)
    
    try:
        # Get merge commits
        commits = get_merge_commits_since(
            since=args.since,
            since_commit=args.since_commit,
        )
        
        # Generate prompt
        generate_cursor_prompt(commits, output_file=args.output)
        
        logger.info("Done! You can now copy the prompt from the output file and use it with Cursor AI.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

