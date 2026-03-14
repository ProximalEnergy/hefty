# Style Guide

## TSX

This project uses `tsc` as the type checker.

Useful commands:

- `pnpm exec tsc`: Checks for type problems in the repository

## Prettier

This project uses `prettier` as the formatter. It is saved as a development dependency in `package.json`. Currently all format rules are defaults.

Useful commands:

- `pnpm add --save-dev prettier@version`: Install a particular version
- `pnpm exec prettier --check .`: Show which files have formatting warnings
- `pnpm exec prettier --write .`: Fix all files that have formatting warnings

### Caveats

- VSCode has a prettier extension which may change prettier version.

## Search Params

Search params can be used to store information about the query that otherwise would be lost in application state. For example, you could store the date range of a query and the project_id which makes sharing the state of a given project page as simple as sharing the url with another user. Examples of good search param usage can be found throughout the application.

## Deprecations

- `src/hooks/types.ts`
- `src/hooks/api.ts`
