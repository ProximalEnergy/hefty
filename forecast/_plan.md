# Implementation Plan: PV Forecast Lambda

## Overview
Build `forecast` as a `uv` workspace Lambda. For configured PV projects,
fetch hourly ECMWF IFS weather through hEFTy, store met forecast, look up
current device metadata, run simplified PVWatts, store POI forecast output.

## Findings
- `forecast/` exists, mostly empty; not in root `uv` workspace.
- `third-party/hefty/` exists as fork; hEFTy supports IFS and hourly solar data.
- ECMWF open data / hEFTy IFS supports 360h, 15 day horizon.
- pv-eem POI output is `p_mp` power in W, clipped by `project.poi * 1_000_000`.
- pv-eem exports POI to `project.data_expected.value` with PV POI power metric.
- Device metadata should be read per run from current DB, not cached in config.
- Existing CDK Docker Lambda pattern lives in `microservices/cdk`.

## Architecture Decisions
- Forecast provider: hEFTy + ECMWF IFS.
- Forecast cadence: hourly hEFTy output.
- Eligibility: explicit project list in `forecast/config.py`.
- Output unit: W at POI, matching pv-eem `p_mp`; hourly energy derived by interval.
- `available_pv_energy_forecast`: don't implement this yet
- CRUD/database access via `DbQuery`.
- Deploy with CDK Docker Lambda, EventBridge schedule.
- env vars will be in AWS secrets manager
- Ignore all static checks inside `third-party/**`.

## Dependency Graph
DB schema -> provider seed -> project eligibility -> weather ingest ->
device metadata lookup -> PVWatts model -> forecast persistence -> CDK deploy.

## Task List

### Phase 1: Foundation
- [ ] Task 1: Workspace + third-party boundary
- [ ] Task 2: Forecast DB schema in `core/src/core/models.py`
- [ ] Task 3: Provider seed + CRUD

### Phase 2: Core Flow
- [ ] Task 4: Eligible project loader
- [ ] Task 5: IFS weather ingest
- [ ] Task 6: Device metadata lookup
- [ ] Task 7: PVWatts POI forecast
- [ ] Task 8: Available forecast mirror

### Checkpoint: Core Flow
- [ ] One configured project writes met + POI forecast rows.

### Phase 3: Deploy
- [ ] Task 9: Lambda handler
- [ ] Task 10: CDK stack + deploy tasks
- [ ] Task 11: focused tests/static checks

### Checkpoint: Complete
- [ ] Lambda scheduled through CDK.
- [ ] Tests mock hEFTy/network.
- [ ] ruff/mypy/knip failures fixed.

## Task 1: Workspace + Third-Party Boundary

**Description:** setup `forecast/`  

**Acceptance criteria:**
- [ ] `forecast` added to root `uv` workspace.
- [ ] local hEFTy dependency resolves from `third-party/hefty`.
- [ ] ruff/mypy/vulture config excludes `third-party/**`.

**Dependencies:** None

**Files likely touched:**
- `pyproject.toml`
- `forecast/pyproject.toml`

**Estimated scope:** Small: 1-2 files

## Task 2: Forecast DB Schema

**Description:** Add models/migrations for provider, met forecast, PV forecast,
and latest forecast storage.

**Acceptance criteria:**
- [ ] `operational.weather_forecast_providers` exists.
- [ ] project tables: `met_forecast`, `met_forecast_latest`,
`pv_energy_forecast`, `available_pv_energy_forecast`.
- [ ] project migrations use `for_each_project_schema`.
- [ ] use existing mise db command to make sure that migration files are correct
- [ ] latest table upsertable by provider/run/forecasted time.
- [ ] output column documented as W at POI despite energy table naming.

**Dependencies:** None

**Files likely touched:**
- `core/src/core/models.py`
- `core/_alembic_migrations/versions/*.py`

**Estimated scope:** Medium: 3-5 files

## Task 3: Provider Seed + CRUD

**Description:** Seed IFS provider and add DbQuery CRUD for forecast tables.

**Acceptance criteria:**
- [ ] stable IFS provider ID seeded.
- [ ] provider CRUD reads by `name_short`.
- [ ] met/PV insert and latest upsert queries use `DbQuery`.

**Dependencies:** Task 2

**Files likely touched:**
- `core/src/core/crud/operational/weather_forecast_providers.py`
- `core/src/core/crud/project/met_forecast.py`
- `core/src/core/crud/project/pv_energy_forecast.py`

**Estimated scope:** Medium: 3-5 files

## Task 4: Eligible Project Loader

**Description:** Load project list from `forecast/config.py`, then query project
metadata needed for weather and POI clipping.

**Acceptance criteria:**
- [ ] config contains eligible project `name_short` values.
- [ ] loader queries project UUID, schema, lat/lon, elevation, timezone, POI.
- [ ] missing/invalid project config fails clearly.

**Dependencies:** Task 3

**Files likely touched:**
- `forecast/config.py`
- `forecast/projects.py`

**Estimated scope:** Small: 1-2 files

## Task 5: IFS Weather Ingest

**Description:** Implement weather port/adaptor around hEFTy IFS hourly output.

**Acceptance criteria:**
- [ ] hEFTy called with IFS and 15 day horizon.
- [ ] rows include run time, forecasted time, provider ID, GHI/DHI/DNI,
ambient temperature, wind speed.
- [ ] writes full history and latest forecast table.
- [ ] tests mock hEFTy output.

**Dependencies:** Tasks 1-4

**Files likely touched:**
- `forecast/weather/port.py`
- `forecast/weather/adaptors/hefty.py`
- `forecast/_tests/**`

**Estimated scope:** Medium: 3-5 files

## Task 6: Device Metadata Lookup

**Description:** Query current project system/device metadata for each run,
borrowing pv-eem source patterns.

**Acceptance criteria:**
- [ ] reads project devices/system layout needed for PVWatts aggregation.
- [ ] reads modules, inverters, rackings via `DbQuery`.
- [ ] no metadata hardcoded in config.
- [ ] missing metadata raises project-specific error and continues next project.

**Dependencies:** Task 4

**Files likely touched:**
- `forecast/pv_energy/metadata.py`
- `core/src/core/crud/project/devices.py`
- `core/src/core/crud/operational/pv_modules.py`
- `core/src/core/crud/operational/inverters.py`
- `core/src/core/crud/operational/rackings.py`

**Estimated scope:** Medium: 3-5 files

## Task 7: PVWatts POI Forecast

**Description:** Run simplified PVWatts from stored met forecast and fresh
metadata, producing pv-eem-compatible POI power.

**Acceptance criteria:**
- [ ] uses pvlib PVWatts APIs.
- [ ] output is W at POI, clipped to `project.poi * 1_000_000`.
- [ ] hourly timestamps align to met forecast timestamps.
- [ ] stored in `project.pv_energy_forecast`.

**Dependencies:** Tasks 5-6

**Files likely touched:**
- `forecast/pv_energy/port.py`
- `forecast/pv_energy/adaptors/pv_watts.py`
- `forecast/_tests/**`

**Estimated scope:** Medium: 3-5 files

## Task 8: Available Forecast Mirror

**Description:** Persist available forecast without downtime subtraction for MVP.

**Acceptance criteria:**
- [ ] `available_pv_energy_forecast` value equals PV forecast value.
- [ ] code names make downtime intentionally absent.
- [ ] no dependency on outage/ticket/energy downtime APIs.

**Dependencies:** Task 7

**Files likely touched:**
- `forecast/pv_energy/availability.py`
- `core/src/core/crud/project/available_pv_energy_forecast.py`

**Estimated scope:** Small: 1-2 files

## Task 9: Lambda Handler

**Description:** Add scheduled Lambda entrypoint that runs configured projects.

**Acceptance criteria:**
- [ ] event can override project list and run time.
- [ ] per-project failures logged without hiding total failure count.
- [ ] handler response includes project success/failure summary.

**Dependencies:** Tasks 4-8

**Files likely touched:**
- `forecast/main.py`
- `forecast/config.py`

**Estimated scope:** Small: 1-2 files

## Task 10: CDK Stack + Deploy Tasks

**Description:** Deploy forecast Lambda through existing CDK microservices app.

**Acceptance criteria:**
- [ ] Dockerfile builds `forecast`, `core`, and local hEFTy dependency.
- [ ] CDK stack creates Lambda, log group, EventBridge schedule (once per day).
- [ ] IAM permits DB/secrets access needed by runtime.
- [ ] `.mise.toml` has forecast deploy/check tasks.

**Dependencies:** Task 9

**Files likely touched:**
- `forecast/Dockerfile`
- `microservices/cdk/app.py`
- `microservices/cdk/stacks/forecast_stack.py`
- `.mise.toml`

**Estimated scope:** Medium: 3-5 files

## Task 11: Tests + Static Checks

**Description:** Add focused tests and fix static failures.

**Acceptance criteria:**
- [ ] hEFTy/network mocked.
- [ ] DbQuery builders tested.
- [ ] PVWatts clipping/unit tests cover W output.
- [ ] if `AGENT_ENVIRONMENT=async-offline`, `mise run check`.

**Dependencies:** Tasks 1-10

**Files likely touched:**
- `forecast/_tests/**`
- `api/_tests/**` if CRUD exposed there

**Estimated scope:** Medium: 3-5 files

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---:|---|
| energy table stores W | High | document unit; consider rename before migration |
| hEFTy/Herbie downloads slow | High | retries, cache config, mocked tests |
| device metadata incomplete | High | fail per project with clear diagnostics |
| PVWatts differs from pv-eem | Med | match POI unit/clipping; compare samples |
| CDK image may need hefty native deps | Med | Docker build test before deploy |

## Open Questions
- Secret/env source for forecast DB credentials?
- Should latest table retain one provider latest run per project, or per run time?
