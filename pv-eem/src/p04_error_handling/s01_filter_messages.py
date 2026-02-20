def filter_messages(message) -> bool:
    """Remove messages"""
    match message:
        case (
            "cannot access local variable 'best_ghi'"
            "where it is not associated with a value"
        ):
            return False
        case _:
            return True
