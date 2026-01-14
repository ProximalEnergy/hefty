# Platform Update Email Scripts

This folder contains scripts and templates to help generate and send platform update emails to users, as well as LinkedIn posts for social media.

## Scripts

### 1. `export_user_emails.py`

Exports all user emails from the database and Clerk into a comma-separated text file that can be easily pasted into the BCC field of an email client.

**Usage:**

```bash
# Export from production (default)
python export_user_emails.py

# Export from development
python export_user_emails.py --env development

# Specify output file
python export_user_emails.py --output emails.txt
```

**Requirements:**

- `DATABASE_URL` environment variable
- `CLERK_SECRET_KEY` (for production) or `CLERK_SECRET_KEY_DEVELOPMENT` (for development)

**Output:**

- Generates a text file with comma-separated email addresses
- Ready to paste into BCC field of email client

## Files

### `email_template.html`

HTML template for platform update emails. Provides consistent styling and structure. Contains placeholders:

- `[DATE_PLACEHOLDER]` - Replace with current date
- `[INTRO_PLACEHOLDER]` - Replace with introduction paragraph
- `[CONTENT_PLACEHOLDER]` - Replace with main content sections

### `cursor_prompt.txt`

Template prompt file for Cursor AI that uses Linear MCP to generate platform update emails and LinkedIn posts. Contains:

- Instructions for using Linear MCP tools to fetch completed issues
- Guidelines for filtering user-facing features
- Formatting guidelines for email and LinkedIn content
- Instructions for generating HTML email, markdown documentation, and LinkedIn post

**Note:** This prompt uses Linear MCP tools (`mcp_linear_list_issues`, `mcp_linear_get_issue`) to fetch completed Linear issues for the target month, making it more accurate than parsing git commits.

### `extract_git_changes.py` (Legacy)

Legacy script that extracts merge commits from git. This has been replaced by the Linear MCP workflow but is kept for reference.

## Workflow

1. **Generate Email and LinkedIn Post with Cursor AI:**

   - Open `cursor_prompt.txt` in Cursor
   - Update the `[MONTH]` and `[YEAR]` placeholders in the prompt
   - Ask Cursor to follow the prompt instructions
   - Cursor will:
     - Use Linear MCP to fetch completed issues for the target month
     - Filter for user-facing features and improvements
     - Generate three files:
       - `platform_update_[MONTH]_[YEAR].html` - HTML email (for email clients)
       - `platform_update_[MONTH]_[YEAR].md` - Markdown version (for documentation)
       - `linkedin_post_[MONTH]_[YEAR].txt` - LinkedIn post (for social media)

2. **Get User Emails:**

   ```bash
   python export_user_emails.py
   ```

3. **Send Email:**

   - Open the generated HTML file (`platform_update_[MONTH]_[YEAR].html`)
   - Copy the HTML content
   - Paste into your email client
   - Paste the comma-separated emails from `user_emails.txt` into the BCC field
   - Send!

4. **Post to LinkedIn:**
   - Open the generated LinkedIn post file (`linkedin_post_[MONTH]_[YEAR].txt`)
   - Copy the content
   - Post to LinkedIn (consider adding relevant images or screenshots if available)

## Notes

- The scripts assume you're in the mono repository root
- Make sure your `.env` file is configured with the necessary credentials for `export_user_emails.py`
- The Linear MCP workflow requires Cursor AI with Linear MCP integration enabled
- Email addresses are exported in a format ready for BCC field (comma-separated)
- The Linear workflow focuses on completed issues that impact users on the frontend, providing more accurate and relevant updates than git-based analysis
