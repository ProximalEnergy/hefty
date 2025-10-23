from sqlalchemy import text
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
