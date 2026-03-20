"""Compare API OpenAPI routes with web-app and internal usages."""

from __future__ import annotations

import argparse
import inspect
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ALLOWED_UNUSED_ROUTES = {
    "/",  # Root path
    "/openapi.json",
    "/docs",
    "/redoc",
    "/v1/admin/user-email",
    "/v1/admin/user-emails",
    "/v1/admin/company-projects/projects/{param}",
    "/v1/operational/projects/{param}/kpi-data/agg",
    "/v1/operational/projects/{param}/kpi-data/agg-freq",
    "/v1/operational/projects/{param}/kpi-data/llm-kpis",
    "/v1/operational/kpi-data/trigger-user-alert",
    "/v1/operational/kpi-data/user-triggered-alerts",
    "/v1/operational/kpi-data/{param}/kpi-email-alerts",
    "/v1/operational/projects/{param}/events/llm-event-losses",
    "/v1/operational/projects/{param}/status/interpret",
    "/v1/operational/projects/{param}/status/time-series-python",
    "/v1/operational/projects/{param}/llm-time-series",
    # Dev/debug endpoints intentionally not used by the web-app.
    "/v1/development/ptp/explore",
    "/v1/development/ptp/markets",
    "/v1/development/ptp/markets/{param}/endpoints",
    "/v1/development/ptp/markets/{param}/endpoints/{param}/data",
    "/v1/development/ptp/markets/{param}/endpoints/{param}/elements",
    "/v1/development/ptp/markets/{param}/endpoints/{param}/schema",
    "/v1/protected/web-application/projects/{param}/market-performance/debug/raw",
    "/v1/protected/web-application/projects/{param}/market-performance/realtime",
}


def normalize_path(*, path: str) -> str:
    """
    Normalize an API path for comparison.

    Args:
        path: The raw path string to normalize.
    """
    # Remove {{baseURL}} if present (common in Hurl/Bruno)
    path = path.replace("{{baseURL}}", "")
    without_query = path.split("?", 1)[0]

    # Replace various path parameter styles with {param}
    # FastAPI: {item_id}, JS Template: ${item_id}, Hurl/Bruno: {{item_id}}
    normalized = re.sub(r"\{[^/]+\}", "{param}", without_query)
    normalized = re.sub(r"\$\{[^}]+\}", "{param}", normalized)
    normalized = re.sub(r"\{\{[^}]+\}\}", "{param}", normalized)

    # Replace numeric segments with {param} to handle hardcoded IDs in tests
    normalized = re.sub(r"/\d+(?=/|$)", "/{param}", normalized)

    # Replace UUIDs with {param}
    normalized = re.sub(
        (
            r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}(?=/|$)"
        ),
        "/{param}",
        normalized,
    )

    # If it doesn't start with / but looks like an API path, add it
    if not normalized.startswith("/") and normalized.startswith(("v1/", "version")):
        normalized = "/" + normalized

    normalized = normalized.rstrip("/")
    return normalized or "/"


def _ts_simple_string_const_map(*, content: str) -> dict[str, str]:
    """Map const names to string literals for simple `const x = '...'` forms."""
    mapping: dict[str, str] = {}
    for name, raw in re.findall(r"\bconst\s+(\w+)\s*=\s*'([^']*)'", content):
        mapping[name] = raw
    for name, raw in re.findall(r'\bconst\s+(\w+)\s*=\s*"([^"]*)"', content):
        mapping[name] = raw
    return mapping


def _strip_leading_param_prefixes(*, path: str) -> str:
    """Remove leading `{param}` segments from a stitched template URL."""
    return re.sub(r"^(?:\{param\})+/?", "", path)


def _interpolate_ts_template(*, template: str, const_map: dict[str, str]) -> str:
    """Replace `${...}`; simple identifiers use const_map, else `{param}`."""

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        if re.fullmatch(r"[A-Za-z_][\w]*", inner):
            return const_map.get(inner, "{param}")
        return "{param}"

    return re.sub(r"\$\{([^}]*)\}", repl, template)


def _iter_ts_template_literal_bodies(*, content: str) -> Iterable[str]:
    """Yield bodies of non-tagged template literals (skip `identifier` patterns)."""
    i = 0
    n = len(content)
    id_tail = re.compile(r"[a-zA-Z0-9_$]$")
    while i < n:
        if content[i] != "`":
            i += 1
            continue
        if i > 0 and id_tail.match(content[i - 1]):
            i += 1
            continue
        buf: list[str] = []
        j = i + 1
        while j < n:
            ch = content[j]
            if ch == "\\":
                buf.append(ch)
                if j + 1 < n:
                    buf.append(content[j + 1])
                    j += 2
                continue
            if ch == "`":
                yield "".join(buf)
                i = j + 1
                break
            buf.append(ch)
            j += 1
        else:
            break


def get_api_paths_with_definitions(*, app: Any) -> dict[str, str]:
    """
    Get a mapping of normalized paths to their source file definitions.

    Args:
        app: The FastAPI application instance.
    """
    repo_root = Path(__file__).resolve().parents[2]
    paths_to_files = {}
    from fastapi.routing import APIRoute

    for route in app.routes:
        if isinstance(route, APIRoute):
            norm_path = normalize_path(path=route.path)
            try:
                # Get the file where the endpoint is defined
                source_file = inspect.getsourcefile(route.endpoint) or inspect.getfile(
                    route.endpoint
                )
                file_path = Path(source_file).resolve()
                if ".venv" in file_path.parts:
                    continue
                rel_path = str(file_path.relative_to(repo_root))
                paths_to_files[norm_path] = rel_path
            except (TypeError, ValueError, AttributeError):
                if norm_path not in paths_to_files:
                    paths_to_files[norm_path] = "unknown"
    return paths_to_files


def get_api_paths_from_schema_dts(*, schema_path: Path) -> set[str]:
    """
    Get API paths from web-app schema.d.ts file.

    Args:
        schema_path: Path to the schema.d.ts file.
    """
    content = schema_path.read_text(encoding="utf-8")
    pattern = re.compile(r'^\s*"(\/[^"]+)"\s*:', re.MULTILINE)
    paths = set()
    for raw_path in pattern.findall(content):
        normalized = normalize_path(path=raw_path)
        paths.add(normalized)
    return paths


def iter_source_files(*, roots: list[Path]) -> Iterable[Path]:
    """
    Iterate over source files in the given root directories.

    Args:
        roots: A list of Path objects to search in.
    """
    extensions = {".ts", ".tsx", ".py", ".hurl", ".bru"}
    ignored_parts = {".venv"}
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix in extensions:
                yield root
            continue
        for path in root.rglob("*"):
            if ignored_parts.intersection(path.parts):
                continue
            if path.suffix in extensions:
                if path.name in {"schema.d.ts", "check_unused_routes.py"}:
                    continue
                yield path


def extract_paths_from_sources(*, roots: list[Path]) -> set[str]:
    """
    Extract all potential API paths from source files.

    TypeScript template literals are stitched using simple `const` string maps.

    Args:
        roots: A list of Path objects to search in.
    """
    # Broad pattern to find potential paths
    pattern = re.compile(r"""/[^"'`\s]+|v1/[^"'`\s]+|version[^"'`\s]*""")
    string_literal = r'(?:`[^`]*`|\'[^\']*\'|"[^"]*")'
    concat_pattern = re.compile(
        rf"({string_literal})(?:\s*\+\s*{string_literal})+",
        re.DOTALL,
    )
    array_join_pattern = re.compile(
        r"""\[\s*(?P<items>[^\]]*)\s*\]\.join\(\s*['"](?P<sep>[^'"]*)['"]\s*\)""",
        re.DOTALL,
    )
    array_item_pattern = re.compile(r"""`[^`]*`|'[^']*'|"[^"]*"|[a-zA-Z0-9_$.]+""")
    found_paths: set[str] = set()

    for path in iter_source_files(roots=roots):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in concat_pattern.finditer(content):
            literal_chain = match.group(0)
            parts = re.findall(string_literal, literal_chain, re.DOTALL)
            combined = "".join(part[1:-1] for part in parts)
            for piece in pattern.findall(combined):
                if piece.startswith("//"):
                    continue
                normalized = normalize_path(path=piece)
                if normalized:
                    found_paths.add(normalized)

        for match in array_join_pattern.finditer(content):
            separator = match.group("sep")
            if separator not in {"/", ""}:
                continue
            items = match.group("items")
            raw_items = array_item_pattern.findall(items)
            if not raw_items:
                continue
            built_items = []
            for item in raw_items:
                if item.startswith(("'", '"', "`")):
                    built_items.append(item[1:-1])
                else:
                    built_items.append("{param}")
            combined = separator.join(built_items)
            if combined.startswith("//"):
                continue
            normalized = normalize_path(path=combined)
            if normalized:
                found_paths.add(normalized)

        if path.suffix in {".ts", ".tsx"}:
            const_map = _ts_simple_string_const_map(content=content)
            for body in _iter_ts_template_literal_bodies(content=content):
                if "/" not in body and "v1/" not in body:
                    continue
                stitched = _interpolate_ts_template(
                    template=body,
                    const_map=const_map,
                )
                stripped = _strip_leading_param_prefixes(path=stitched)
                if stripped:
                    normalized_tpl = normalize_path(path=stripped)
                    if normalized_tpl and normalized_tpl != "/":
                        found_paths.add(normalized_tpl)
                    for piece in pattern.findall(stitched):
                        if piece.startswith("//"):
                            continue
                        normalized_piece = normalize_path(path=piece)
                        if normalized_piece and normalized_piece != "/":
                            found_paths.add(normalized_piece)

        for match in pattern.findall(content):
            if match.startswith("//"):
                continue
            normalized = normalize_path(path=match)
            if normalized:
                found_paths.add(normalized)
    return found_paths


def main() -> int:
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(description="Check for unused API routes")
    parser.add_argument(
        "--mode",
        choices=["openapi", "app"],
        default="app",
        help=(
            "Mode: 'openapi' for fast CI checks (no file grouping), "
            "'app' for detailed local checks (with file grouping)"
        ),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]

    if args.mode == "openapi":
        # Fast mode: use generated web-app schema.d.ts
        schema_path = repo_root / "web-app" / "src" / "api" / "schema.d.ts"
        if not schema_path.exists():
            print(
                "schema.d.ts not found. "
                "Run 'mise run root:codegen' to generate it."
            )
            return 1

        api_paths = get_api_paths_from_schema_dts(schema_path=schema_path)
        api_paths_map = {}
    else:
        # Detailed mode: inspect the app
        os.environ.setdefault("ENVIRONMENT", "development")
        from app.main import app

        api_paths_map = get_api_paths_with_definitions(app=app)
        api_paths = set(api_paths_map.keys())

    search_roots = [
        repo_root / "web-app" / "src",
        repo_root / "api" / "_tests",
        repo_root / "api" / "_smoke_testing",
        repo_root / "api" / "_scripts",
        repo_root / "api" / "_data_insert",
        repo_root / "api" / "app",
    ]

    found_paths = extract_paths_from_sources(roots=search_roots)

    allowed = ALLOWED_UNUSED_ROUTES
    used_allowed = sorted((allowed & found_paths) & api_paths)
    unused_paths = sorted(api_paths - found_paths - allowed)

    if used_allowed:
        print("Allowed-unused routes are referenced in sources:")
        for path in used_allowed:
            print(f"  - {path}")
        return 1

    if unused_paths:
        print("Unused API routes (not referenced in web-app or internal tests):")

        if args.mode == "app" and api_paths_map:
            # Group by file for cleaner output
            by_file = defaultdict(list)
            for path in unused_paths:
                file_path = api_paths_map.get(path, "unknown")
                by_file[file_path].append(path)

            for file_path in sorted(by_file.keys()):
                print(f"\nIn {file_path}:")
                for path in sorted(by_file[file_path]):
                    print(f"  - {path}")
        else:
            # Simple list for OpenAPI mode
            for path in unused_paths:
                print(f"  - {path}")

        return 1

    print("All API routes are referenced in web-app or internal tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
