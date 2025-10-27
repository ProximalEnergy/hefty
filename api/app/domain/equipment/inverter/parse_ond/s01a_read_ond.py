import io
from typing import Any


def read_ond(*, file_content: bytes) -> dict:
    """
    Read and parse an ONDx file.

    Args:
        file_path: The full path to the ONDx file

    Returns:
        A dictionary containing the parsed ONDx data
    """
    with io.StringIO(file_content.decode("utf-8-sig")) as file:
        lines = [
            line.rstrip()
            for line in file
            if line.strip() and not line.startswith("End of")
        ]

    root: dict[str, Any] = {}
    stack = [(-1, root)]  # (indent_level, parent_dict)

    for i, line in enumerate(lines):
        # Calculate current indentation
        indent = len(line) - len(line.lstrip())
        current_line = line.strip()

        # Find the appropriate parent based on indentation
        while stack and indent <= stack[-1][0]:
            stack.pop()

        current_parent = stack[-1][1]

        # Check if this is a key-value pair
        if "=" in current_line:
            key, value = map(str.strip, current_line.split("=", 1))

            # Check if next line has greater indentation
            if i + 1 < len(lines):
                next_indent = len(lines[i + 1]) - len(lines[i + 1].lstrip())
                if next_indent > indent:
                    # Value is a section header, create nested dict
                    new_dict: dict[str, Any] = {}
                    current_parent[key] = {value: new_dict}
                    stack.append((indent, current_parent[key]))
                    stack.append((next_indent, new_dict))
                else:
                    current_parent[key] = value
            else:
                current_parent[key] = value
        else:
            # Section header without '='
            new_dict = {}
            current_parent[current_line] = new_dict
            stack.append((indent, new_dict))

    return root
