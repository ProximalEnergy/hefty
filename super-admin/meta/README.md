# Meta

Small terminal UI for the mono repo.

It shows the top 20 files from the last 3 months, with sorting by either
git line churn or touches.

It excludes lockfiles, `schema.d.ts`, and `*.csv`.

## Run

From `super-admin/meta`:

1. `uv sync`
2. `uv run meta`

Keys:

- `r` refresh
- `s` toggle sort mode
- `l` sort by line churn
- `t` sort by touches
- `q` quit
