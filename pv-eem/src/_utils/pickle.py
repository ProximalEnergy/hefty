import importlib
import os
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class NotImplementedButOkay:
    message: str = "Not implemented in PROD or STAGE, but this is intended"


# --- FUNCTIONS ---
def _import_dill() -> Any:
    """Load dill lazily because it is only required for DEV workflows."""
    return importlib.import_module("dill")


def export_class_to_dill(
    self: type[Any],
    filepath: str,
):
    """Exports a class to a dill file.

    Args:
        self: The class isntance to export
        filepath: The path where the dill file should be saved

    Raises:
        TypeError: If cls is not a class
        OSError: If there are file permission issues
    """
    dill = _import_dill()

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    # Export the class
    with open(filepath, "wb") as f:
        dill.dump(self, f)


def import_class_from_dill(filepath: str, ENVIRONMENT: str) -> type[Any]:
    """Run import_class_from_dill."""
    match ENVIRONMENT:
        case "DEV":
            dill = _import_dill()

            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")

            with open(filepath, "rb") as f:
                loaded_obj: object = dill.load(f)

            if not isinstance(loaded_obj, type):
                raise TypeError("Expected a class object in dill file")

            return loaded_obj
        case "PROD" | "STAGE":
            return NotImplementedButOkay
        case _:
            raise ValueError("ENVIRONMENT must be DEV, STAGE, or PROD")
