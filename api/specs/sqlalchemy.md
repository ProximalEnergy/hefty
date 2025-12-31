# SQLAlchemy Spec (API)

API (mono/api) uses SQLAlchemy 2.0. This document outlines the best practices for using SQLAlchemy in API.

## DO

- Use `where()` instead of `filter()`. For example, use `query = select(models.UserType).where(models.UserType.user_type_id == user_type_id)`.