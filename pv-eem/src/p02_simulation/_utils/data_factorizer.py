"""Factorization utilities for generating group IDs from DataFrame columns."""

import pandas as pd


def factorize(
    *,
    dataframe: pd.DataFrame,
    columns: list,
    rounding_precision: int | None = 0,
    separator: str = "-",
) -> pd.DataFrame:
    """Create a group ID column by factorizing unique combinations of specified columns.

    This function generates integer group IDs for unique combinations of values
    across specified columns. It's commonly used to optimize calculations by
    grouping rows with identical parameter combinations. The group ID is always
    stored in a column named "_unique_id".

    Parameters
    ----------
    dataframe : pd.DataFrame
        The input DataFrame to add the group ID column to
    columns : List[str]
        List of column names to use for creating unique combinations
    rounding_precision : Optional[int], default None
        Number of decimal places to round numeric values to before factorization.
        If None, no rounding is applied.
    separator : str, default "-"
        String used to join column values when creating the combination key
    offset : int, default 1
        Value to add to the factorized results (useful for making IDs start from 1)

    Returns:
    -------
    pd.DataFrame
        The input DataFrame with the new "_unique_id" column added

    Examples:
    --------
    >>> df = pd.DataFrame({
    ...     'a': [1, 2, 1, 2],
    ...     'b': [10, 20, 10, 30],
    ...     'c': [100, 200, 100, 200]
    ... })
    >>> result = factorize(
    ...     dataframe=df,
    ...     columns=['a', 'b'],
    ...     rounding_precision=0
    ... )
    >>> result['unique_id'].tolist()
    [1, 2, 1, 3]
    """
    df = dataframe.copy()

    # Extract the specified columns
    selected_columns = df[columns]

    # Apply rounding if specified
    if rounding_precision is not None:
        selected_columns = selected_columns.round(rounding_precision)

    # Convert to string and join with separator
    combination_key = selected_columns.astype(str).agg(separator.join, axis=1)

    # Create group IDs using factorize
    offset = 1
    df["_unique_id"] = pd.factorize(combination_key)[0] + offset

    return df
