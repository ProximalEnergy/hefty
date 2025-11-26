#!/usr/bin/env python3
"""Check that functions enforce keyword-only arguments via ``*``."""

from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

HTTP_METHOD_DECORATORS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "options",
    "head",
    "route",
    "api_route",
    "websocket",
    "websocket_route",
}


class FunctionVisitor(ast.NodeVisitor):
    """Collect functions that do not enforce keyword-only arguments."""

    def __init__(self) -> None:
        self.errors: list[tuple[int | None, int | None, str | None]] = []
        self.source_lines: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._check_function(node=node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._check_function(node=node)
        self.generic_visit(node)

    def _check_function(self, *, node: ast.AST) -> None:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            return

        has_skip_comment = False
        if self.source_lines:
            try:
                line_index = node.lineno - 1
                if line_index < len(self.source_lines):
                    line = self.source_lines[line_index]
                    if "# skip-star-syntax" in line:
                        has_skip_comment = True

                if line_index > 0 and not has_skip_comment:
                    prev_line = self.source_lines[line_index - 1]
                    if "# skip-star-syntax" in prev_line:
                        has_skip_comment = True
            except (AttributeError, IndexError):
                pass

        has_exemption_decorator = False
        for decorator in getattr(node, "decorator_list", []):
            if is_fastapi_route_decorator(decorator=decorator):
                has_exemption_decorator = True
                break

        only_has_self = False
        args = getattr(node, "args", None)
        if (
            args
            and len(args.args) == 1
            and not args.kwonlyargs
            and not getattr(args, "posonlyargs", [])
        ):
            if args.args[0].arg == "self":
                only_has_self = True

        has_params = False
        if args:
            has_params = (
                bool(args.args)
                or bool(args.kwonlyargs)
                or bool(getattr(args, "posonlyargs", []))
            )

        if not has_params or only_has_self:
            return

        has_star_arg = False
        if args:
            has_star_arg = (
                bool(args.kwonlyargs) or bool(args.vararg) or bool(args.kwarg)
            )

        if not has_star_arg and self.source_lines:
            try:
                source_lines = self.source_lines[node.lineno - 1 : node.end_lineno]
                function_source = "\n".join(source_lines)
                if re.search(r"def\s+\w+\s*\([^)]*\*[^*)]", function_source):
                    has_star_arg = True
            except (AttributeError, IndexError):
                pass

        if (
            not has_exemption_decorator
            and not has_skip_comment
            and has_params
            and not has_star_arg
        ):
            function_name = getattr(node, "name", "<unknown>")
            message = (
                f"Function '{function_name}' must use '*' in parameters to enforce "
                "keyword arguments"
            )
            self.errors.append(
                (
                    getattr(node, "lineno", None),
                    getattr(node, "col_offset", None),
                    message,
                )
            )

    def set_source_lines(self, *, source_lines: list[str]) -> None:
        self.source_lines = source_lines


def parse_args(*, argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure Python functions enforce keyword-only arguments using '*'"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific files or directories to check",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        help=(
            "Directory to scan when no explicit paths are provided. "
            "Defaults to the current working directory."
        ),
    )
    return parser.parse_args(argv)


def resolve_paths(
    *, paths: Iterable[str], default_directory: Path | None
) -> list[Path]:
    resolved: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.is_dir():
            resolved.extend(find_python_files(directory=path))
        elif path.suffix == ".py" and path.exists():
            resolved.append(path)
    if not resolved and default_directory is not None:
        directory = default_directory
        if not directory.is_absolute():
            directory = Path.cwd() / directory
        if not directory.exists():
            logging.error("Directory '%s' not found", directory)
            return []
        resolved = find_python_files(directory=directory)
    if not resolved:
        logging.warning("No Python files to check")
    return resolved


def find_python_files(*, directory: Path) -> list[Path]:
    python_files: list[Path] = []
    for path in directory.rglob("*.py"):
        if path.is_file():
            python_files.append(path)
    return python_files


def check_file(*, filename: Path) -> list[tuple[int | None, int | None, str | None]]:
    try:
        content = filename.read_text(encoding="utf-8")
        source_lines = content.splitlines()
        tree = ast.parse(content, filename=str(filename))
        visitor = FunctionVisitor()
        visitor.set_source_lines(source_lines=source_lines)
        visitor.visit(tree)
        return visitor.errors
    except SyntaxError as error:
        return [(error.lineno, error.offset, f"Syntax error: {error}")]
    except Exception as error:  # noqa: BLE001
        return [(None, None, f"Error processing file {filename}: {error}")]


def is_fastapi_route_decorator(*, decorator: ast.AST) -> bool:
    if isinstance(decorator, ast.Name):
        return decorator.id == "router"
    if isinstance(decorator, ast.Attribute):
        return decorator.attr == "router"
    if not isinstance(decorator, ast.Call):
        return False
    func = decorator.func
    if isinstance(func, ast.Name):
        return func.id == "router"
    if not isinstance(func, ast.Attribute):
        return False
    attribute_chain = _extract_attribute_chain(node=func)
    if not attribute_chain:
        return False
    base_name = attribute_chain[0]
    attr_name = attribute_chain[-1]
    if attr_name == "router":
        return True
    if attr_name not in HTTP_METHOD_DECORATORS:
        return False
    return base_name == "app" or "router" in base_name


def _extract_attribute_chain(*, node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return _extract_attribute_chain(node=node.value) + [node.attr]
    return []


def main(*, argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv=argv)
    search_directory = args.directory
    files = resolve_paths(paths=args.paths, default_directory=search_directory)
    if not files:
        if search_directory is not None:
            directory = search_directory
            if not directory.is_absolute():
                directory = Path.cwd() / directory
            if not directory.exists():
                return 1
        return 0

    has_errors = False
    for filename in files:
        errors = check_file(filename=filename)
        if errors:
            has_errors = True
            try:
                display_path = filename.relative_to(Path.cwd())
            except ValueError:
                display_path = filename
            logging.error("Errors in %s:", display_path)
            for line, col, message in errors:
                if line is not None and col is not None:
                    logging.error("  Line %s, Col %s: %s", line, col, message)
                else:
                    logging.error("  %s", message)

    return 1 if has_errors else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    sys.exit(main())
