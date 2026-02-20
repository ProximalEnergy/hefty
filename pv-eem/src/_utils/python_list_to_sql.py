def convert_list_to_sql_string(python_list):
    """Convert a Python list to a SQL-compatible string for use in IN clauses
    Handles strings, numbers, and None values appropriately

    Args:
        python_list (list): List of items to convert

    Returns:
        str: SQL-formatted string suitable for IN clause

    Example:
        >>> list_to_sql_string([1, 'apple', None, 3.14])
        "(1, 'apple', NULL, 3.14)"
    """
    if len(python_list) == 0:
        return "(NULL)"  # Return valid SQL for empty list

    def format_item(item):
        if item is None:
            return "NULL"
        elif isinstance(item, int | float):
            return str(item)
        else:
            # Escape single quotes by replacing ' with ''
            return "'{}'".format(str(item).replace("'", "''"))

    formatted_items = [format_item(item) for item in python_list]
    return "({})".format(", ".join(formatted_items))
