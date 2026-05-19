# Style Guide

## TSX

This project uses `tsgo` as the type checker.

Useful commands:

- `pnpm exec tsgo`: Checks for type problems in the repository

## Search Params

Search params can be used to store information about the query that otherwise would be lost in application state. For example, you could store the date range of a query and the project_id which makes sharing the state of a given project page as simple as sharing the url with another user. Examples of good search param usage can be found throughout the application.

## Deprecations

- `src/hooks/types.ts`
- `src/hooks/api.ts`
