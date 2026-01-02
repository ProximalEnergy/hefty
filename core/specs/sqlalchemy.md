# SQLAlchemy Spec (Core)

Core (mono/core) uses SQLAlchemy 2.0. This document outlines the best practices for using SQLAlchemy in Core.

## DO

- Use `Session.execute()` instead of `Session.query()`. For example, use `session.execute(select(models.User))`. ([Reference](https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.execute))
- Use `where()` instead of `filter()`. For example, use `query = select(models.UserType).where(models.UserType.user_type_id == user_type_id)`.