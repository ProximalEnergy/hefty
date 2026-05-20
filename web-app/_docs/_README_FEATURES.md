# Features

This directory holds **feature slices** aligned with
[Bulletproof React](https://github.com/alan2207/bulletproof-react): colocate
code by domain, keep features self-contained, and expose a small public API
through route entry files. Do not add barrel files. Outside the feature, import
only route entry components from `@/features/<group>/<feature>/routes/...`.

## Domain groups

Organize features under a **group** folder that reflects the product area, for
example `performance/` or `maintenance/`. Add new groups when a domain does not
fit an existing one.

## Feature folder layout

Each **feature** is a single folder (e.g. `performance/met-station/`). Inside
it, use only the subfolders you need. Allowed subfolders (do not add others):

| Folder       | Purpose                                               |
| ------------ | ----------------------------------------------------- |
| `components` | Presentational and composite UI used by this feature  |
| `hooks`      | React hooks (state, wiring, context consumers)        |
| `queries`    | Data-fetch hooks and query-layer glue                 |
| `routes`     | Route-level components wired to the router            |
| `types`      | TypeScript types and interfaces for this feature      |
| `utils`      | Pure helpers, builders, normalizers                   |
| `views`      | Larger screens or tab panels composed from components |

## Public API

Feature root `index.ts` barrels are not allowed. Other parts of the app may
import only route entry components from `routes/<Feature>Route.tsx`. Do not
import feature internals unless there is a deliberate, documented exception.

## Deviations from Bulletproof React

A few documented departures from
[upstream Bulletproof React](https://github.com/alan2207/bulletproof-react):

- **Queries are shared, not feature-local.** Most query hooks live in
  `@/api/v1/...` and `@/hooks/api` instead of co-located `queries/` folders. Our
  API is generalized enough that most endpoints serve multiple pages, so those
  hooks belong in shared locations. Use a feature's `queries/` folder only for
  hyper-specific hooks with a single caller, sparingly.
- **Features are grouped by product domain.** We nest features under
  `src/features/<group>/<feature>/` (e.g. `performance/met-station/`) rather
  than the flat `src/features/<feature>/` upstream layout.
- **Routes are co-located inside features.** Upstream BR puts route components
  under `src/app/routes/`; we keep them in the feature at
  `features/<group>/<feature>/routes/`. The app-level `App.tsx` still owns the
  route _paths_.
- **The subfolder list is closed and enforced.** Allowed: `components`,
  `hooks`, `queries`, `routes`, `types`, `utils`, `views`. We do not use
  `api/`, `assets/`, or `stores/` — assets live in `src/assets/`, API hooks in
  `@/api/v1/...`, and state goes through React Query or context. The
  conformance script (`scripts/check-bulletproof-react.mjs`) blocks any
  unknown subfolder.

## Reference

See `performance/met-station/` for a full example: `routes/` for the entry
component, `views/` for tab content, `hooks/` and `queries/` for data and UI
state, `components/` for shared UI within the feature, `types/` and `utils/` for
types and pure logic.
