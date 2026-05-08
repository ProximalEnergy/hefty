# Issues Pipeline

## Run the pipeline locally
- Install toolchain and deps:
  - `mise install`
  - `uv sync --project issues`
- Run one pipeline pass:
  - `uv run --project issues python -m issues.orchestrator.run_issues`
- Output behavior:
  - The runner discovers active projects from `operational.projects` (read-only).
  - Normal scheduled runs evaluate a two-hour lookback window.
  - Detector context is read from project schemas via `core`.
  - Issue lifecycle is persisted to project DB tables.
  - Rotating logs are written beside orchestration scripts.

## Run backfill manually
Backfill is set up to run any arbitrary combination of (project_ids, start, end, issue_category_ids). `start` and `end` are required, while None for `project_ids` and `issue_category_ids` will run the backfill for all. Backfills run in 1-day intervals over the requested period.

This is a dumb way to invoke this, but it will be improved later.
```
uv run --project issues python -c '
from issues.lambda_handler import lambda_handler
event = {
  "project_ids": None,
  "issue_category_ids": None,
  "start": "2026-04-01",
  "end": "2026-04-03"
}
print(lambda_handler(event, None))
'
```

## High-level functional overview
- `issues/orchestrator/run_issues.py`
  - Discovers project scope and runs each project.
- `issues/orchestrator/run_project.py`
  - Builds detector registry.
  - Merges detector data requirements.
  - Pulls union data once into shared `DetectorContext`.
  - Runs each detector and combines all candidates.
  - Applies rectification and persists via DB-backed issue repository.
- `issues/orchestrator/context_builder.py`
  - Executes one tags query and one timeseries query per project run.
- `issues/detectors/*`
  - Detector modules emit normalized `IssueCandidate` objects.
- `issues/rectification/*`
  - De-duplicates / normalizes candidate stream before persistence.
- `issues/persistence/db_repository.py`
  - Handles open/match/resolve lifecycle in project DB tables.
- `issues/persistence/run_repository.py`
  - DB repository factory for orchestrator use.
- `issues/logging_utils.py`
  - Shared rotating file + stdout logging setup helper.

## Workflow for adding a detector
1. Add a detector module in `issues/detectors/`.
2. Add detector config dataclass fields in `issues/config/issue_detectors.py`.
3. In `issues/orchestrator/run_project.py`:
   - Instantiate the detector in `_build_configured_detectors`.
   - Define its `DetectorDataRequirements` (device/sensor/window/interval).
4. Reuse shared context:
   - If detector needs only existing context fields, no context changes needed.
   - If it needs new context fields, extend `DetectorContext` and populate them in
     `context_builder.py`.
5. Add/update focused tests in `core/tests/issues/test_pipeline.py` or detector tests.

## Current state and integration roadmap
- Current state:
  - Detector registry exists but currently contains one detector:
    `met_station_non_communicating`.
  - Reads are from existing DB tables through `core` helpers.
  - Writes are DB-backed through `core.crud` issue helpers.
  - Run/project/context/persistence paths emit structured INFO logs.
  - Matching lifecycle semantics (open/match/resolve/re-open episode) are active.
- To fully integrate:
  1. Wire scheduler/worker execution for periodic project runs.
  2. Add operational telemetry/metrics (run duration, candidate counts, failures).
  3. Expand detector catalog and add detector-specific test coverage.
  4. Add retries/guards around transient DB failures in orchestration.
