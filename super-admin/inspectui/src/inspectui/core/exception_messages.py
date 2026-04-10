"""User-facing text for common exception patterns."""

import re

_ENUM_MISSING_MEMBER = re.compile(
    r"type object '((?:Device|Sensor)Type)' has no attribute '([^']+)'"
)


def format_exception_message(exc: BaseException) -> str:
    """Return a short hint when the pattern is recognized, else ``str(exc)``."""
    seen: set[int] = set()
    chain: list[BaseException] = []
    stack: list[BaseException] = [exc]
    while stack:
        e = stack.pop()
        if id(e) in seen:
            continue
        seen.add(id(e))
        chain.append(e)
        if e.__cause__ is not None:
            stack.append(e.__cause__)
        ctx = e.__context__
        if ctx is not None and ctx is not e.__cause__:
            stack.append(ctx)

    for e in chain:
        if isinstance(e, AttributeError):
            m = _ENUM_MISSING_MEMBER.search(str(e))
            if m:
                enum_name, member = m.groups()
                return (
                    f"Looks like {enum_name}.{member} does not exist. "
                    "Perhaps it was removed or you made a typo?"
                )
    return str(exc)
