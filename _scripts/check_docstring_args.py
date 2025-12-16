#!/usr/bin/env python3
"""Ensure functions with parameters include an Args block in docstrings."""

from __future__ import annotations

import argparse
import ast
import logging
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import NamedTuple


class DocstringError(NamedTuple):
    """Represents a missing Args block error."""

    filename: Path
    lineno: int | None
    col_offset: int | None
    message: str


class FunctionVisitor(ast.NodeVisitor):
    """Collect functions missing Args/Arguments sections."""

    def __init__(self) -> None:
        """TODO: add description.

        Args:
            self: TODO: describe.
        """
        self.errors: list[DocstringError] = []
        self.source_lines: list[str] = []
        self.filename: Path | None = None

    def set_source_context(
        self,
        *,
        filename: Path,
        source_lines: list[str],
    ) -> None:
        """TODO: add description.

        Args:
            self: TODO: describe.
            filename: TODO: describe.
            source_lines: TODO: describe.
        """
        self.filename = filename
        self.source_lines = source_lines

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """TODO: add description.

        Args:
            self: TODO: describe.
            node: TODO: describe.
        """
        self._check_function(node=node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """TODO: add description.

        Args:
            self: TODO: describe.
            node: TODO: describe.
        """
        self._check_function(node=node)
        self.generic_visit(node)

    def _check_function(self, *, node: ast.AST) -> None:
        """TODO: add description.

        Args:
            self: TODO: describe.
            node: TODO: describe.
        """
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            return

        if should_skip(node=node, source_lines=self.source_lines):
            return

        args = getattr(node, "args", None)
        if not args:
            return

        arg_count = (
            len(getattr(args, "posonlyargs", []))
            + len(args.args)
            + len(args.kwonlyargs)
        )

        if arg_count == 0:
            return

        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            self._add_error(node=node, message="Missing docstring with Args section")
            return

        if not has_args_block(docstring=docstring):
            message = "Docstring must include an Args or Arguments section"
            self._add_error(node=node, message=message)

    def _add_error(self, *, node: ast.AST, message: str) -> None:
        """TODO: add description.

        Args:
            self: TODO: describe.
            node: TODO: describe.
            message: TODO: describe.
        """
        self.errors.append(
            DocstringError(
                filename=self.filename or Path("<unknown>"),
                lineno=getattr(node, "lineno", None),
                col_offset=getattr(node, "col_offset", None),
                message=message,
            )
        )


def should_skip(*, node: ast.AST, source_lines: list[str]) -> bool:
    """Return whether the function should be skipped.

    Args:
        node: TODO: describe.
        source_lines: TODO: describe.
    """
    if not hasattr(node, "lineno"):
        return False

    indices = [getattr(node, "lineno") - 1, getattr(node, "lineno") - 2]
    for index in indices:
        if index < 0:
            continue
        if index >= len(source_lines):
            continue
        if "# skip-args-doc" in source_lines[index]:
            return True
    return False


def has_args_block(*, docstring: str) -> bool:
    """Return True if docstring has an Args/Arguments section.

    Args:
        docstring: TODO: describe.
    """
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped in {"Args:", "Arguments:"}:
            return True
    return False


def parse_args(*, argv: Sequence[str] | None = None) -> argparse.Namespace:
    """TODO: add description.

    Args:
        argv: TODO: describe.
    """
    parser = argparse.ArgumentParser(
        description="Ensure Python docstrings include Args sections for api or core"
    )
    parser.add_argument(
        "repository",
        choices=["api", "core"],
        help="Repository to check (api or core)",
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
            "Defaults to the repository directory."
        ),
    )
    return parser.parse_args(argv)


def resolve_paths(
    *,
    paths: Iterable[str],
    default_directory: Path | None,
) -> list[Path]:
    """TODO: add description.

    Args:
        paths: TODO: describe.
        default_directory: TODO: describe.
    """
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
        if directory.exists():
            resolved = find_python_files(directory=directory)
        else:
            logging.error("Directory '%s' not found", directory)
    if not resolved:
        logging.warning("No Python files to check")
    return resolved


def find_python_files(*, directory: Path) -> list[Path]:
    """TODO: add description.

    Args:
        directory: TODO: describe.
    """
    exclude_dirs = {
        ".venv",
        "venv",
        "site-packages",
        "__pycache__",
        "node_modules",
        "_alembic_migrations",
        "_tests",
        "tests",
    }
    python_files: list[Path] = []
    for path in directory.rglob("*.py"):
        if any(part in exclude_dirs for part in path.parts):
            continue
        if path.is_file():
            python_files.append(path)
    return python_files


def check_file(*, filename: Path) -> list[DocstringError]:
    """TODO: add description.

    Args:
        filename: TODO: describe.
    """
    try:
        content = filename.read_text(encoding="utf-8")
        source_lines = content.splitlines()
        tree = ast.parse(content, filename=str(filename))
        visitor = FunctionVisitor()
        visitor.set_source_context(filename=filename, source_lines=source_lines)
        visitor.visit(tree)
        return visitor.errors
    except SyntaxError as error:
        message = f"Syntax error: {error}"
        return [
            DocstringError(
                filename=filename,
                lineno=error.lineno,
                col_offset=error.offset,
                message=message,
            )
        ]
    except Exception as error:  # noqa: BLE001
        message = f"Error processing file {filename}: {error}"
        return [
            DocstringError(
                filename=filename,
                lineno=None,
                col_offset=None,
                message=message,
            )
        ]


def main(*, argv: Sequence[str] | None = None) -> int:
    """TODO: add description.

    Args:
        argv: TODO: describe.
    """
    args = parse_args(argv=argv)

    # Determine the default directory based on repository argument
    if args.directory:
        default_directory = args.directory
    else:
        # Find the mono repository root (assumes script is in mono/_scripts)
        script_path = Path(__file__).resolve()
        mono_root = script_path.parent.parent
        default_directory = mono_root / args.repository

    paths = resolve_paths(paths=args.paths, default_directory=default_directory)

    all_errors: list[DocstringError] = []
    for path in paths:
        all_errors.extend(check_file(filename=path))

    for error in all_errors:
        location = f"{error.filename}"
        if error.lineno is not None:
            location += f":{error.lineno}"
            if error.col_offset is not None:
                location += f":{error.col_offset}"
        print(f"{location}: {error.message}")

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
