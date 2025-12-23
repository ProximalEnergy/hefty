"""Compare API OpenAPI routes with web-app and internal usages."""

from __future__ import annotations

import inspect
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute


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
        r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)",
        "/{param}",
        normalized,
    )

    # If it doesn't start with / but looks like an API path, add it
    if not normalized.startswith("/") and normalized.startswith(("v1/", "version")):
        normalized = "/" + normalized

    normalized = normalized.rstrip("/")
    return normalized if normalized else "/"


def get_api_paths_with_definitions(*, app: Any) -> dict[str, str]:
    """
    Get a mapping of normalized paths to their source file definitions.

    Args:
        app: The FastAPI application instance.
    """
    repo_root = Path(__file__).resolve().parents[2]
    paths_to_files = {}
    for route in app.routes:
        if isinstance(route, APIRoute):
            norm_path = normalize_path(path=route.path)
            try:
                # Get the file where the endpoint is defined
                source_file = inspect.getsourcefile(route.endpoint) or inspect.getfile(
                    route.endpoint
                )
                file_path = Path(source_file).resolve()
                rel_path = str(file_path.relative_to(repo_root))
                paths_to_files[norm_path] = rel_path
            except (TypeError, ValueError, AttributeError):
                if norm_path not in paths_to_files:
                    paths_to_files[norm_path] = "unknown"
    return paths_to_files


def allowed_unused_routes() -> set[str]:
    """
    Get the set of routes that are allowed to be unused.

    Returns:
        A set of normalized path strings.
    """
    return {
        "/",  # Root path
        "/openapi.json",
        "/docs",
        "/redoc",
        "/v1/admin/user-email",
        "/v1/admin/user-emails",
        "/v1/admin/company-projects/projects/{param}",
    }


def iter_source_files(*, roots: list[Path]) -> Iterable[Path]:
    """
    Iterate over source files in the given root directories.

    Args:
        roots: A list of Path objects to search in.
    """
    extensions = {".ts", ".tsx", ".py", ".hurl", ".bru"}
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix in extensions:
                yield root
            continue
        for path in root.rglob("*"):
            if path.suffix in extensions:
                if path.name in {"schema.d.ts", "check_unused_routes.py"}:
                    continue
                yield path


def extract_paths_from_sources(*, roots: list[Path]) -> set[str]:
    """
    Extract all potential API paths from source files.

    Args:
        roots: A list of Path objects to search in.
    """
    # Broad pattern to find potential paths
    pattern = re.compile(r"""/[^"'`\s]+|v1/[^"'`\s]+|version[^"'`\s]*""")
    found_paths: set[str] = set()

    for path in iter_source_files(roots=roots):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in pattern.findall(content):
            normalized = normalize_path(path=match)
            if normalized:
                found_paths.add(normalized)
    return found_paths


def main() -> int:
    """
    Main entry point for the script.
    """
    os.environ.setdefault("ENVIRONMENT", "development")

    from app.main import app

    api_paths_map = get_api_paths_with_definitions(app=app)
    api_paths = set(api_paths_map.keys())

    repo_root = Path(__file__).resolve().parents[2]

    search_roots = [
        repo_root / "web-app" / "src",
        repo_root / "api" / "_tests",
        repo_root / "api" / "_smoke_testing",
        repo_root / "api" / "_scripts",
        repo_root / "api" / "_data_insert",
        repo_root / "api" / "app",
    ]

    found_paths = extract_paths_from_sources(roots=search_roots)

    allowed = allowed_unused_routes()
    unused_paths = sorted(api_paths - found_paths - allowed)

    if unused_paths:
        print("Unused API routes (not referenced in web-app or internal tests):")
        # Group by file for cleaner output
        by_file = defaultdict(list)
        for path in unused_paths:
            file_path = api_paths_map.get(path, "unknown")
            by_file[file_path].append(path)

        for file_path in sorted(by_file.keys()):
            print(f"\nIn {file_path}:")
            for path in sorted(by_file[file_path]):
                print(f"  - {path}")
        return 1

    print("All API routes are referenced in web-app or internal tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
