# Style Guide

## Routes

Generally, routes can be found in `app.v1._category_`. A common pattern is to have the actual route be a thin wrapper around the actual business logic function so that the business logic function can be used in other parts of the application if needed.

## Linting

- Linting is managed by `ruff` and is configured in `pyproject.toml
- Additional linting is managed by `mypy` which can be turned off in-line with `# type: ignore`

## Function Style

- Functions should use the `*` syntax at the beginning (or near the beginning) of each list of parameters in order to ensure that only keyword arguments are allowed. Lint can be ignored with `# nosemgrep: python-enforce-keyword-only-args`
- Pandas functions should not use the `inplace=bool` kwarg if the linter accidentally blocks one of these you can comment `# noqa: inplace`

## Pre commit hooks

- Pre-commit hooks set up in `.pre-commit-config.yaml` to run linting code on every commit.
- You will need to have `pre-commit` installed in your virtual environment
- The command `pre-commit install` will install all hooks into your .git folder so that they can be run on every commit.

## Pydantic

We use `pydantic` to serialize and validate inputs and outputs to/from the API. You will find the top level interfaces in `app.interfaces.py`. Subsets can be created as child `pydantic` interfaces in their corresponding `_crud` files.

# Ruff Rules Proposed

| Category | Number | Description                                          |
| -------- | ------ | ---------------------------------------------------- |
| A        |        | (LATER) shadowing of python built-ins                |
| FAST     | 002    | (LATER) FastAPI: non-annotated dependency.           |
| ANN      |        | (LATER) Type annotations, will slow us down          |
| S        |        | Security lints (flake8-bandit) (user aims to adopt). |
| B        |        | Catches various bugs/design issues (flake8-bugbear). |
| BLE      |        | (LATER) Discourages blind `except` blocks.           |
| C        |        | Unnecessary list/dict comprehensions/literals.       |
| DTZ      |        | Datetime timezone awareness.                         |
| LOG      |        | (LATER) Logging statement checks.                    |
| G        |        | (LATER) Logging string formatting style.             |
| INP      |        | Implicit namespace package detection.                |
| PIE      |        | Code simplification (flake8-pie).                    |
| T        |        | `print` statement usage (flake8-print).              |
| PT       |        | Pytest style conventions.                            |
| Q        |        | String quote style (flake8-quotes).                  |
| RET      |        | Return statement consistency.                        |
| SIM      |        | Code simplification (flake8-simplify).               |
| SLOT     |        | `__slots__` usage (flake8-slots).                    |
| TID      |        | Import tidiness and banned APIs.                     |
| TC       |        | Type checking block imports.                         |
| ARG      |        | Unused function/method arguments.                    |
| PTH      |        | `pathlib` usage over `os.path`.                      |
| FLY      |        | F-string conversion (flynt).                         |
| NPY      |        | NumPy specific lints.                                |
| N        |        | PEP8 naming conventions.                             |
| PD       |        | Pandas specific lints.                               |
| PERF     |        | Performance anti-patterns (Perflint).                |
| F        |        | Logical errors (Pyflakes).                           |
| PLC      |        | Pylint convention checks.                            |
| PLE      |        | Pylint error checks.                                 |
| PLR      |        | Pylint refactoring suggestions.                      |
| PLW      |        | Pylint warning checks.                               |
| Up       |        | Python syntax upgrades (pyupgrade).                  |
| Ruff     |        | Ruff-specific lints.                                 |

# Ruff Rules Rejected

| Category | Number | Description                                            |
| -------- | ------ | ------------------------------------------------------ |
| AIR      |        | Airflow specific rules (not used).                     |
| COM      | COM819 | Prohibits trailing commas (user prefers them).         |
| CPY      |        | Missing copyright notice.                              |
| D        |        | Pydocstyle docstring conventions.                      |
| DJ       |        | Django specific rules (not used)                       |
| DOC      |        | Pydoclint docstring validation.                        |
| E        |        | Pycodestyle (PEP8) style errors. (too pedantic)        |
| EM       |        | Exception message string formatting. (too pedantic)    |
| ERA      |        | Finds commented-out code (too pedantic)                |
| FIX      |        | FIXME/TODO comment style.                              |
| FBT      |        | Boolean positional arguments (conflicts with FastAPI). |
| PGH      |        | Pygrep-hooks specific lints.                           |
| W        |        | Pycodestyle (PEP8) style warnings.                     |
| PYI      |        | Stub file (.pyi) linting (not used).                   |
| TD       |        | TODO comment standards.                                |
| YTT      |        | Code modernization for year 2000 (obsolete)            |
