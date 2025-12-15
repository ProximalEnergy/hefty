# generate_ts_enums.py
# NOTE object as const is better than TS enum at compile time!

import importlib.util
import inspect
from enum import Enum, IntEnum
from types import ModuleType
from typing import Any


def load_module_from_path(path: str) -> ModuleType:
    """Handle load module from path.

    Args:
        path: TODO: describe.
    """
    spec = importlib.util.spec_from_file_location("enum_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def is_enum_class(obj: Any) -> bool:
    """Return whether is enum class.

    Args:
        obj: TODO: describe.
    """
    return inspect.isclass(obj) and issubclass(obj, Enum) and obj is not Enum


def enum_members_in_order(enum_cls: type[Enum]) -> list[Enum]:
    # For IntEnum (and your BaseIntEnum), sort numerically by value.
    # For others (e.g., StrEnum), preserve definition order (the class' __members__.values()).
    """Handle enum members in order.

    Args:
        enum_cls: TODO: describe.
    """
    members = list(enum_cls)  # iteration preserves definition order in CPython
    if issubclass(enum_cls, IntEnum):
        return sorted(members, key=lambda m: int(m.value))
    return members


def ts_literal(value: Any) -> str:
    """Handle ts literal.

    Args:
        value: TODO: describe.
    """
    if isinstance(value, str):
        # Escape basic characters for TS string literal
        s = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    # numbers (ints/floats) or other JSON-serializable primitives
    return str(value)


def enum_to_ts_constant(enum_cls: type[Enum]) -> str:
    """Handle enum to ts constant.

    Args:
        enum_cls: TODO: describe.
    """
    name = enum_cls.__name__
    lines: list[str] = [f"export const {name}Enum = {{"]
    for m in enum_members_in_order(enum_cls):
        lines.append(f"  {m.name}: {ts_literal(m.value)},")
    lines.append("} as const;")
    return "\n".join(lines)


def main():
    # Hardcoded paths
    """Handle main."""
    input_path = "../core/src/core/enumerations.py"
    output_path = "../web-app/src/api/enumerations.ts"

    mod = load_module_from_path(input_path)

    # Collect all top-level Enum classes from the module
    enums: list[type[Enum]] = []
    for _, obj in inspect.getmembers(mod, predicate=inspect.isclass):
        if obj.__module__ != mod.__name__:
            continue  # skip imported classes
        if is_enum_class(obj):
            # skip the base class itself (e.g., BaseIntEnum) if you don't want it emitted
            if obj.__name__.startswith("_"):
                continue
            enums.append(obj)

    # Stable alphabetical order by class name for output
    enums.sort(key=lambda c: c.__name__)

    # Emit a file header and all constants
    out: list[str] = [
        "// Auto-generated. Do not edit by hand.",
        "// Generated with generate_ts_enums.py",
        "",
    ]
    for i, enum_cls in enumerate(enums):
        out.append(enum_to_ts_constant(enum_cls))
        if i < len(enums) - 1:
            out.append("")  # blank line between constants

    # Write to file instead of printing to stdout
    with open(output_path, "w") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    main()
