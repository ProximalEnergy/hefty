"""
This is a module which directly implements the python 3.9 standard library distutils.
Because distutils was deprecated in Python 3.10 and removed in Python 3.12,
this module provides a backport of the distutils API for Python 3.9.
"""


def strtobool(*, val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

        True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
        are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
        'val' is anything else.

    Args:
        val: TODO: describe.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"invalid truth value {val!r}")
