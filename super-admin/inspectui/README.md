# InspectUI

Terminal UI for working with mono project/device/tag data: pick active projects, load data from Postgres or CSV, run data-quality tests, and review results. **Core logic** (`src/inspectui/core/`) is separate from **curses UI** (`src/inspectui/tui/`) so logic can be reused or re-skinned later.

## Run

From `**super-admin/inspectui`**:

1. `uv sync`
2. Set `**DATABASE_URL**` (or a `.env` file in the working directory).
3. `uv run python -m inspectui` (or `uv run inspectui`).

This package depends on the sibling `**core**` library (`path = "../../core"` in `pyproject.toml`).

## What the menus do

- **Manage Active Projects** — Choose which projects tests and downloads apply to. Stored in `~/.inspectui/config.yaml`.
- **Download Active Projects (Database)** — Load devices/tags from Postgres into the cache under `~/.inspectui/cache/`.
- **Load Active Projects (CSV)** — Devices from `{name_short} - devices.csv` inside `csv_data_root` (default `~/Downloads` if present). Tags are still loaded from the database for that project.
- **Run Tests** — Runs selected built-in tests using parameters from `**test_params.py`**, with optional overrides from config (see below). There is **no** in-app parameter editor.
- **Last Test Run Results** — Shows the last saved summary from disk.

## Keys

Most screens print a one-line hint. Globally: **arrows** or **j/k** move, **Enter** confirms, **Space** toggles in multi-select lists, **q** goes back or quits. Some screens add **r** (refresh), **f** / **m** (test results filters), **/** (project filter), etc.—read the line on screen.

## Configuration and cache


| What                                                               | Where                                                    |
| ------------------------------------------------------------------ | -------------------------------------------------------- |
| User settings: active projects, optional `test_params.{test_name}` | `~/.inspectui/config.yaml`                               |
| Cached project payload (project + devices + tags)                  | `~/.inspectui/cache/{name_short}.json`                   |
| Team-wide list of projects hidden from the picker                  | `src/inspectui/core/repo_config.py` → `IGNORED_PROJECTS` |
| Versioned default test parameters                                  | `src/inspectui/core/tests/test_params.py`                |


**Test parameter precedence:** For each key, `config.yaml` under `test_params.<test_name>` overrides `test_params.py`. Any parameter still unset uses the default in the test class definition (`TestParameter.default`).

## Built-in tests

Registered in `src/inspectui/core/tests/builtin/`. Defaults belong in `test_params.py`.


| Test name                       | Purpose                                                    |
| ------------------------------- | ---------------------------------------------------------- |
| `sensor_type_unique_per_device` | At most one tag per device for each configured sensor type |
| `parent_device_type_allowlist`  | Child device types must have an allowed parent type        |
| `required_device_models`        | Selected device types must have `device_model_id` set      |


To add a test: subclass `**BaseTest`**, decorate with `**@TestRegistry.register**`, define `**parameters**` if needed, implement `**run()**`, and add a `**TEST_PARAMS**` entry when you want shared defaults. Builtin registration happens when `inspectui.core.tests` is imported.

## Where to change code

- **Queries and columns** — `core/fetcher.py`, `core/csv_loader.py` (keep `core/models.py` in sync).
- **Cache format** — `core/cache.py`.
- **New menu flow** — `tui/screens/main_menu.py` and a new or existing screen under `tui/screens/`.
- **Widgets** — `tui/components/` (`ListSelector`, prompts, etc.).

Do not duplicate SQL or full schema here; treat `**fetcher.py`** and `**csv_loader.py**` as the source of truth for columns.

## Suggested prompts (for AI or future you)

- *Add a built-in test named … that …. Register it and add defaults in `test_params.py`.*
- *Add a new column to devices: update `DeviceInfo`, `fetcher`, `csv_loader`, and cache round-trip.*
- *Add a main-menu action that … and a screen in `tui/screens/`.*
- *Change how test results are filtered or summarized in `test_results.py`.*

## Dependencies

Listed in `**pyproject.toml*`* (upper-bounded ranges for repo policy). Uses `**uv**` and the editable `**core**` package.