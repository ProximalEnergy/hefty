def combine_tier_codes(x):
    # Flatten list of lists into a single set of unique values
    unique_values = set()
    for item in x:
        # Assuming items are stored as strings and need to be evaluated as lists
        if isinstance(item, str):
            # Remove brackets and split by comma
            values = item.strip("[]").replace("'", "").split(",")
            # Add each stripped value to the set
            unique_values.update(value.strip() for value in values)
    return list(unique_values)
