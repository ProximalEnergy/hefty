"""Build an HTML table of all uploaded project documents (S3 presigned links)."""

from __future__ import annotations

import argparse
import html
import sys
import webbrowser
from pathlib import Path
from typing import Any

import boto3
import polars as pl
from core.db_query import DbQuery
from core.enumerations import OutputType
from dotenv import load_dotenv
from sqlalchemy import select

from core import models

BUCKET_NAME = "proximal-am-documents"
REGION_NAME = "us-east-2"
PRESIGN_EXPIRES = 3600

_HTML_PREFIX = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Uploaded project documents</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1.5rem; }
    h1 { font-size: 1.25rem; }
    .toolbar { margin-bottom: 1rem; }
    #search { width: min(100%, 24rem); padding: 0.35rem 0.5rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }
    th { background: #f0f0f0; user-select: none; }
    th:hover { background: #e0e0e0; }
    a { color: #06c; }
  </style>
</head>
<body>
  <h1>Uploaded project documents</h1>
  <p>Filter and sort in the browser. Presigned links expire in about 1 hour.</p>
  <div class="toolbar">
    <label for="search">Search: </label>
    <input type="search" id="search" placeholder="Filter by any column…" />
  </div>
  <div class="toolbar">
    <label for="search-doc">Document: </label>
    <input type="search" id="search-doc" placeholder="Document…" />
    <label for="search-company" style="margin-left: 0.75rem;">Company: </label>
    <input type="search" id="search-company" placeholder="Company…" />
    <label for="search-project" style="margin-left: 0.75rem;">Project: </label>
    <input type="search" id="search-project" placeholder="Project…" />
  </div>
  <table id="docs">
    <thead>
      <tr>
        <th>Document</th>
        <th>Company</th>
        <th>Project</th>
        <th>View</th>
      </tr>
    </thead>
    <tbody>
"""

_HTML_SUFFIX = """
    </tbody>
  </table>
  <script>
  (function () {
    const table = document.getElementById("docs");
    const tbody = table.querySelector("tbody");
    const search = document.getElementById("search");
    const searchDoc = document.getElementById("search-doc");
    const searchCompany = document.getElementById("search-company");
    const searchProject = document.getElementById("search-project");
    const headers = table.querySelectorAll("thead th");
    let sortState = { col: null, asc: true };

    function getCellSortKey(tr, colIdx) {
      const td = tr.children[colIdx];
      if (colIdx === 3) {
        const a = td.querySelector("a");
        return a ? (a.getAttribute("href") || "") : "";
      }
      return (td.textContent || "").trim();
    }

    function applyFilter() {
      const q = (search.value || "").trim().toLowerCase();
      const qDoc = (searchDoc.value || "").trim().toLowerCase();
      const qCompany = (searchCompany.value || "").trim().toLowerCase();
      const qProject = (searchProject.value || "").trim().toLowerCase();
      tbody.querySelectorAll("tr").forEach((tr) => {
        const cells = tr.children;
        const docText = (cells[0]?.textContent || "").toLowerCase();
        const companyText = (cells[1]?.textContent || "").toLowerCase();
        const projectText = (cells[2]?.textContent || "").toLowerCase();
        const rowText = (tr.textContent || "").toLowerCase();

        const okGlobal = !q || rowText.includes(q);
        const okDoc = !qDoc || docText.includes(qDoc);
        const okCompany = !qCompany || companyText.includes(qCompany);
        const okProject = !qProject || projectText.includes(qProject);

        tr.style.display =
          okGlobal && okDoc && okCompany && okProject ? "" : "none";
      });
    }

    function sortRows(colIdx) {
      const rows = Array.from(tbody.querySelectorAll("tr"));
      if (sortState.col === colIdx) {
        sortState.asc = !sortState.asc;
      } else {
        sortState.col = colIdx;
        sortState.asc = true;
      }
      const mult = sortState.asc ? 1 : -1;
      rows.sort((a, b) => {
        const ca = getCellSortKey(a, colIdx).toLowerCase();
        const cb = getCellSortKey(b, colIdx).toLowerCase();
        if (ca < cb) { return -1 * mult; }
        if (ca > cb) { return 1 * mult; }
        return 0;
      });
      rows.forEach((r) => { tbody.appendChild(r); });
      applyFilter();
    }

    headers.forEach((th, i) => {
      th.addEventListener("click", function () { sortRows(i); });
    });
    search.addEventListener("input", applyFilter);
    searchDoc.addEventListener("input", applyFilter);
    searchCompany.addEventListener("input", applyFilter);
    searchProject.addEventListener("input", applyFilter);
  })();
  </script>
</body>
</html>
"""


def _generate_presigned_url(*, file_key: str) -> str:
    """Return a GET presigned URL for the given S3 object key.

    Args:
        file_key: S3 object key in ``proximal-am-documents`` (us-east-2).
    """
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    return str(
        s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": file_key},
            ExpiresIn=PRESIGN_EXPIRES,
        )
    )


def _document_display_name(*, s3_key: str) -> str:
    """Return the filename segment of the S3 key (matches API behavior)."""
    return s3_key.rsplit("/", maxsplit=1)[-1] if s3_key else ""


def _row_to_html(*, s3_key: str, company_name: str, project_name: str) -> str:
    """Build one table row with escaped text and a presigned link cell."""
    name = _document_display_name(s3_key=s3_key)
    url = _generate_presigned_url(file_key=s3_key)
    link_html = (
        f'<a href="{html.escape(url)}" target="_blank" '
        'rel="noopener noreferrer">View</a>'
    )
    return (
        "<tr>"
        f"<td>{html.escape(name)}</td>"
        f"<td>{html.escape(company_name)}</td>"
        f"<td>{html.escape(project_name)}</td>"
        f"<td>{link_html}</td>"
        "</tr>\n"
    )


def _dataframe_to_html_rows(*, frame: pl.DataFrame) -> str:
    """Render all rows; presigns one URL per document."""
    if frame.is_empty():
        return '<tr><td colspan="4">No documents found.</td></tr>\n'

    parts: list[str] = []
    for row in frame.to_dicts():
        s3 = str(row.get("s3_key", "") or "")
        company = str(row.get("company_name_long", "") or "")
        project = str(row.get("project_name_long", "") or "")
        parts.append(
            _row_to_html(
                s3_key=s3,
                company_name=company,
                project_name=project,
            )
        )
    return "".join(parts)


def build_html_report(
    *,
    frame: pl.DataFrame,
) -> str:
    """Assemble the full self-contained HTML document string.

    Args:
        frame: Polars rows with ``s3_key``, ``company_name_long``,
            ``project_name_long``.
    """
    body_rows = _dataframe_to_html_rows(frame=frame)
    return _HTML_PREFIX + body_rows + _HTML_SUFFIX


def _load_uploaded_documents(*, output_type: OutputType) -> Any:
    """Load uploaded documents joined to company + project names.

    Args:
        output_type: Output type for `DbQuery.get()` (prefer POLARS).
    """
    stmt = (
        select(
            models.Document.document_id,
            models.Document.s3_key,
            models.Company.name_long.label("company_name_long"),
            models.Project.name_long.label("project_name_long"),
        )
        .join(
            models.Company,
            models.Document.company_id == models.Company.company_id,
        )
        .join(
            models.Project,
            models.Document.project_id == models.Project.project_id,
        )
        .order_by(
            models.Company.name_long,
            models.Project.name_long,
            models.Document.s3_key,
        )
    )
    return DbQuery(query=stmt).get(schema="operational", output_type=output_type)


def main(argv: list[str] | None = None) -> int:
    """Load documents from the database and write a browsable HTML report.

    Args:
        argv: Optional command-line args (default: ``sys.argv[1:]``).
    """
    _ = load_dotenv()
    parser = argparse.ArgumentParser(
        description="List all uploaded project documents and open an HTML report.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.cwd() / "uploaded-documents.html",
        help="Path to write the HTML file (default: ./uploaded-documents.html)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the report in a browser after writing.",
    )
    ns = parser.parse_args(argv)
    out_path: Path = ns.output

    raw: Any = _load_uploaded_documents(output_type=OutputType.POLARS)
    if not isinstance(raw, pl.DataFrame):
        sys.stderr.write("Unexpected query result (expected Polars).\n")
        return 1
    report = build_html_report(frame=raw)
    out_path.write_text(report, encoding="utf-8")
    sys.stdout.write(f"Wrote {out_path.resolve()}\n")
    if not ns.no_open:
        webbrowser.open(out_path.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
