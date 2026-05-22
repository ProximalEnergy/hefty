"""Link Griffe metadata objects to imported Python objects."""

from __future__ import annotations

import importlib
from typing import Any

from griffe import Alias, Object


def import_from_path(*, dotted_path: str) -> Any:
    """Import an attribute reachable from a dotted path."""
    parts = dotted_path.split(".")
    for i in range(len(parts), 0, -1):
        mod_name = ".".join(parts[:i])
        try:
            module = importlib.import_module(mod_name)
            break
        except ImportError:
            continue
    else:
        msg = f"Could not import a module prefix of {dotted_path!r}"
        raise ImportError(msg)

    obj: Any = module
    for attr in parts[i:]:
        obj = getattr(obj, attr)
    return obj


def runtime_object(*, griffe_obj: Object | Alias) -> Any | None:
    """Live Python object for Griffe metadata, or None if import fails."""
    try:
        resolved: Object = (
            griffe_obj.final_target if isinstance(griffe_obj, Alias) else griffe_obj
        )
        return import_from_path(dotted_path=resolved.path)
    except Exception:
        return None
