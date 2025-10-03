#!/usr/bin/env python3
import ast
import logging
import os
import re
import sys


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.source_lines = []

    def visit_FunctionDef(self, node):
        # Check if the function has a skip comment by examining source code
        has_skip_comment = False
        if self.source_lines:
            try:
                # Check for the comment in the function definition line
                line_index = node.lineno - 1
                if line_index < len(self.source_lines):
                    line = self.source_lines[line_index]
                    if "# skip-star-syntax" in line:
                        has_skip_comment = True

                # Also check the line above for the comment
                if line_index > 0 and not has_skip_comment:
                    prev_line = self.source_lines[line_index - 1]
                    if "# skip-star-syntax" in prev_line:
                        has_skip_comment = True
            except (AttributeError, IndexError):
                pass

        # Skip functions decorated with @router from FastAPI
        has_exemption_decorator = False
        for decorator in node.decorator_list:
            # Check for @router as a simple name
            if isinstance(decorator, ast.Name) and decorator.id == "router":
                has_exemption_decorator = True
                break

            # Check for @something.router as an attribute
            elif isinstance(decorator, ast.Attribute) and decorator.attr == "router":
                has_exemption_decorator = True
                break

            # Check for @router.get(), @router.post(), etc. as method calls
            elif isinstance(decorator, ast.Call) and isinstance(
                decorator.func,
                ast.Attribute,
            ):
                # Check if it's a method on the 'router' object
                if (
                    isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "router"
                ):
                    has_exemption_decorator = True
                    break

        # Check if the function only has 'self' as parameter
        only_has_self = False
        if (
            len(node.args.args) == 1
            and not node.args.kwonlyargs
            and not (hasattr(node.args, "posonlyargs") and node.args.posonlyargs)
        ):
            # Check if the single parameter is named 'self'
            if node.args.args[0].arg == "self":
                only_has_self = True

        # Skip functions that don't have any parameters or only have 'self'
        has_params = (
            bool(node.args.args)
            or bool(node.args.kwonlyargs)
            or (hasattr(node.args, "posonlyargs") and bool(node.args.posonlyargs))
        )

        # If the function has no parameters or only has self, no need to enforce star
        # syntax
        if not has_params or only_has_self:
            self.generic_visit(node)
            return

        # Check if the function has a star (*) parameter
        has_star_arg = (
            node.args.kwonlyargs
            or (hasattr(node.args, "vararg") and node.args.vararg is not None)
            or (hasattr(node.args, "kwarg") and node.args.kwarg is not None)
        )

        # Also check for * (bare star parameter) by examining source code
        if not has_star_arg and self.source_lines:
            try:
                source_lines = self.source_lines[node.lineno - 1 : node.end_lineno]
                function_source = "\n".join(source_lines)
                # Look for a pattern like 'def func(param1, *, param2)' or 'def func(*)'
                if re.search(r"def\s+\w+\s*\([^)]*\*[^*)]", function_source):
                    has_star_arg = True
            except (AttributeError, IndexError):
                pass

        if (
            not has_exemption_decorator
            and not has_skip_comment
            and not only_has_self
            and has_params
            and not has_star_arg
        ):
            self.errors.append(
                (
                    node.lineno,
                    node.col_offset,
                    f"Function '{node.name}' must use '*' in parameters to "
                    f"enforce keyword arguments",
                ),
            )

        # Continue visiting child nodes
        self.generic_visit(node)

    def set_source_lines(self, *, source_lines):
        self.source_lines = source_lines


def check_file(
    *,
    filename: str,
) -> list[tuple[int | None, int | None, str | None]]:
    try:
        with open(filename, encoding="utf-8") as f:
            content = f.read()
            source_lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=filename)
            visitor = FunctionVisitor()
            visitor.set_source_lines(source_lines=source_lines)
            visitor.visit(tree)
            return visitor.errors
        except SyntaxError as e:
            return [(e.lineno, e.offset, f"Syntax error: {e}")]
    except Exception as e:
        return [(None, None, f"Error processing file {filename}: {str(e)}")]


def find_python_files(directory):
    """Find all Python files in the given directory and its subdirectories."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files


def main():
    # Check if specific files were provided as arguments
    files = None

    # If no files provided, check all Python files in the app directory
    if not files:
        app_dir = "src"
        if os.path.isdir(app_dir):
            files = find_python_files(app_dir)
            logging.info(
                f"Found {len(files)} Python files in the '{app_dir}' directory",
            )
        else:
            logging.error(f"Directory '{app_dir}' not found")
            return 1

    if not files:
        logging.warning("No Python files to check")
        return 0

    has_errors = False
    for filename in files:
        if not filename.endswith(".py"):
            continue

        errors = check_file(filename=filename)
        if errors:
            has_errors = True
            logging.error(f"Errors in {filename}:")
            for line, col, message in errors:
                if line is not None and col is not None:
                    logging.error(f"  Line {line}, Col {col}: {message}")
                else:
                    logging.error(f"  {message}")

    return 1 if has_errors else 0


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    sys.exit(main())
