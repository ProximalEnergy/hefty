import asyncio
from pathlib import Path

import tomli


async def get_simulation_version() -> str:
    """Get simulation version from the pyproject.toml file"""
    # --- Execution ---
    # Find pyproject.toml relative to this file's location
    current_file = Path("pyproject.toml")
    try:

        def _read_toml_file() -> dict:
            with current_file.open("rb") as f:
                return tomli.load(f)

        pyproject = await asyncio.to_thread(_read_toml_file)
        version: str = pyproject["project"]["version"]

    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find pyproject.toml at {current_file}")

    return version
