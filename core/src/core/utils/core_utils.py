import pandas as pd
from sqlalchemy import text
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session


def get_table_columns(
    db: Session, *, table_name: str, schema: str = "operational"
) -> list[str]:
    stmt = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :tablename
          AND table_schema = :schemaname
        ORDER BY ordinal_position
    """
    cols = db.execute(text(stmt).bindparams(tablename=table_name, schemaname=schema))
    return [col[0] for col in cols]


def model_list_to_pandas[T](*, model_list: list[T]) -> pd.DataFrame:
    """
    Quick and dirty conversion from list of SQLAlchemy models to pandas DataFrame.
    No relation to ModelList or ModelItem.

    Args:
        model_list: List of SQLAlchemy model instances

    Returns:
        pandas.DataFrame with model attributes as columns
    """
    if not model_list:
        return pd.DataFrame()

    # Get column attributes from the first object (assuming all objects are same type)
    first_obj = model_list[0]
    column_attrs = inspect(first_obj).mapper.column_attrs  # type: ignore

    # Create list of dictionaries with model attributes
    data = [
        {col.key: getattr(obj, col.key) for col in column_attrs} for obj in model_list
    ]

    return pd.DataFrame(data)
