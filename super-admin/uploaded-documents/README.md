# uploaded-documents

Small CLI for developers: loads **all** uploaded project documents from the
database, writes a static HTML file, and opens it in your browser. The page
includes a **search** box and **clickable column headers** to sort; presigned
S3 links expire in about one hour.

## Prerequisites

- `DATABASE_URL` (same as other mono tools; load via `.env` in the current
  directory or your environment)
- AWS credentials with permission to presign `GetObject` on
  `proximal-am-documents` (us-east-2)

## Run

From this directory:

1. `uv sync`
2. `uv run uploaded-documents`

Options:

- `-o` / `--output` — path for the HTML file (default: `./uploaded-documents.html`)
- `--no-open` — only write the file, do not launch a browser

## What it does

- Queries `operational.documents` joined to uploader company and project
  names (via `core.crud.operational.documents.get_all_uploaded_documents_with_companies`)
- Embeds one presigned view link per row; filtering and sorting happen entirely
  in the browser (no server).
