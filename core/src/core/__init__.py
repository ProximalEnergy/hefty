from . import crud, dependencies, domain, enumerations, utils

__all__ = ["crud", "dependencies", "domain", "enumerations", "utils"]


def core_main() -> str:
    return "Hello from core!"
