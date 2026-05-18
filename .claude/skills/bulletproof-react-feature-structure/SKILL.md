---
name: bulletproof-react-feature-structure
description: Defines the Bulletproof React (Proximal variant) feature structure used in web-app/src/features/. Covers folder layout (closed list of seven subfolders, grouped by product domain), naming conventions (PascalCase .tsx for component-exporting files, kebab-case .ts for everything else), the context + view-model hook pattern, the data-layer split (queries usually shared, not feature-local), route wiring, loading/error placement, URL state, and component prop typing. Use whenever creating a new feature, refactoring or scaffolding files under src/features/, splitting a legacy pages/.../page.tsx into a feature, or reviewing changes in those areas. Reference implementation: web-app/src/features/performance/met-station/. After changes, run pnpm check:bulletproof-react (or pnpm check) — that is the conformance gate.
---

Reference implementation: `web-app/src/features/performance/met-station/`. High-level intent and named deviations from upstream Bulletproof React: `web-app/_docs/_README_FEATURES.md`. Mechanical enforcement: `pnpm check:bulletproof-react` (also part of `pnpm check`).

This skill is the Claude Code counterpart to the Cursor rule at `web-app/.cursor/rules/bulletproof-react-feature-structure.mdc`. Same source of truth, same `.cursor/rules/`-style globs — Cursor and Claude Code stay isolated by directory.

# Folder layout

Features live under `web-app/src/features/<group>/<feature>/` where `<group>` is a product domain (`performance`, `maintenance`, ...). Add a new group only when no existing one fits.

Allowed feature subfolders (do not add others):

- `components` — Presentational/composite UI used by this feature
- `hooks` — React hooks (state, wiring, context consumers)
- `queries` — Feature-local data hooks (use sparingly; see Data layer)
- `routes` — Route-level entry components
- `types` — TypeScript types for this feature
- `utils` — Pure helpers, builders, normalizers
- `views` — Larger screens or tab panels composed from components

Inside a feature, use only the subfolders you need. Do NOT add `api/`, `assets/`, `stores/`, or any other folder. The conformance script will fail on unknown subfolders.

# Public API

Every feature exports its public surface through `index.ts` — typically the route component only:

```ts
// web-app/src/features/performance/met-station/index.ts
export { MetStationRoute } from './routes/MetStationRoute'
```

Outside callers import from `@/features/<group>/<feature>` (which resolves to `index.ts`). Never reach into a deep subpath of another feature, in any form (absolute `@/features/<g>/<f>/<sub>` or relative `../../<f>/<sub>`). Both are flagged by the conformance script.

# File naming

- PascalCase `.tsx` when the file's primary export is a React component. Symbol matches filename. Examples: `MetStationRoute.tsx`, `DayView.tsx`, `Tabs.tsx`.
- kebab-case `.ts` for everything else. Examples: `use-met-station-context.ts`, `build-time-search-params.ts`, `met-station.ts`.
- `hooks/*.ts` and `queries/*.ts` must match `use-<kebab>.ts` (queries are data hooks).
- Folders are always kebab-case (`met-station`, never `MetStation` or `met_station`).

# Imports

- Within a feature: relative paths (`../components/Tabs`, `../hooks/use-met-station-tab`).
- Across features or to shared code: absolute via `@/` (`@/components/PageTitle`, `@/api/enumerations`).
- Features never import from other features in any form. This includes:
  - Absolute: `import x from '@/features/<other>/...'`
  - Relative: `import x from '../../<other-feature>/...'`
  - Side-effect: `import '@/features/<other>'` (bare, no `from`)

If you find yourself wanting to import across features, the cross-cutting piece belongs in `web-app/src/components/`, `web-app/src/hooks/`, or `web-app/src/lib/`. Lift it up first, then both features import the shared version.

# Data layer

Most query hooks are NOT feature-local. The API is general enough that endpoints serve multiple pages, so query hooks live in shared locations:

- `@/api/v1/...` — endpoint hooks
- `@/hooks/api` — `useCustomQuery` and friends

Use a feature's `queries/` folder only for hyper-specific hooks with a single caller. Keep this rare.

Per the `_README_FEATURES.md`: *"Most queries and data hooks are not co-located with their associated features. Our API is generalized enough that most endpoints touch multiple pages, so those hooks usually belong in shared API or query-layer locations anyway."*

# Context and view-model hooks

Each feature exposes one **context hook** that aggregates the queries every view in the feature needs. Each view has its own **view-model hook** that shapes data for that view.

**Context hook** (`hooks/use-<feature>-context.ts`): aggregates queries the whole feature needs. Returns `{ <ids>, <entities>, isLoading, error }`. The route checks `isLoading`/`error` once and passes the resolved context down to views.

**View-model hook** (`hooks/use-<feature>-<view>-view-model.ts`): one per view. Takes `{ context, ...viewParams }`, returns the shape the view renders. Composes shared API hooks — never calls axios directly.

```tsx
function FeatureRoute() {
  const context = useFeatureContext({ projectId })
  if (context.isLoading) return <PageLoader />
  if (context.error !== null) return <PageError text="..." />
  return <Tabs>{activeTab === 'x' && <XView context={context} />}</Tabs>
}

function XView({ context }: { context: FeatureContext }) {
  const data = useFeatureXViewModel({ context, ...params })
  return <Layout>...</Layout>
}
```

Reference: `web-app/src/features/performance/met-station/hooks/use-met-station-context.ts`, `web-app/src/features/performance/met-station/hooks/use-met-station-day-view-model.ts`, `web-app/src/features/performance/met-station/views/DayView.tsx`.

# Routes and app wiring

- Route components live at `routes/<Feature>Route.tsx` inside the feature.
- `App.tsx` (or an existing `pages/.../page.tsx`) imports the route from the feature's barrel:
  `import { MetStationRoute } from '@/features/performance/met-station'`
- During migration, the existing `pages/.../page.tsx` becomes a one-line shim so router definitions in `App.tsx` don't move:

```tsx
import { MetStationRoute } from '@/features/performance/met-station'

export default function Page() {
  return <MetStationRoute />
}
```

Route paths themselves live in `App.tsx`. Features only export the route component.

# Loading and errors

- At the route boundary: `<PageLoader />` while the context is loading; `<PageError text="..." />` on error or missing required entities.
- Inside views: per-card `<Skeleton>` wrappers around content while individual queries load. Don't gate the whole view on one chart's loading state.

# URL state for tabs

Tab state belongs in the URL via `useSearchParams`. Provide a `use<Feature>Tab` hook returning `{ activeTab, setActiveTab }`, with a self-healing `useEffect` that writes the default tab into the URL when missing. Reference: `web-app/src/features/performance/met-station/hooks/use-met-station-tab.ts`.

# Component prop typing

Inline `type <Component>Props = { ... }` declared just above the component. Use `type` (not `interface`) for component props inside a feature.

```tsx
type DayViewProps = { context: MetStationContext }

export function DayView({ context }: DayViewProps) { ... }
```

# Red Flags

- Cross-feature imports of any form (absolute, relative, or side-effect).
- Reaching into another feature's internals instead of importing from its `index.ts`.
- Adding subfolders other than the seven listed above (no `api/`, `assets/`, `stores/`).
- Putting fetcher functions inline in components — go through `@/hooks/api` or `@/api/v1/...`.
- Defining route paths inside a feature — paths live in `App.tsx`.
- Gating an entire view on one query's `isLoading` when per-card skeletons would do.

# Common Rationalizations

| Excuse | Rebuttal |
| --- | --- |
| "I just need a `stores/` (or `api/`, or `assets/`) folder for this one feature." | Folders outside the allowed seven are not permitted. State goes through React Query or context; assets live in `web-app/src/assets/`; API hooks in `@/api/v1/...`. The conformance script blocks unknown subfolders. |
| "I'll inline the route path in `routes/Route.tsx` so the feature is self-contained." | Route paths live in `App.tsx`. Features only export the route component. Splitting the path from the feature limits blast radius when routing changes. |
| "Within my own feature it's clearer to absolute-import via `@/features/<self>/...`." | Within a feature, use relative paths. Absolute `@/features/<self>/...` imports trigger a warning (`self-deep-absolute-import`). The barrel is for *external* callers only. |
| "The view can call `useQuery` directly — wrapping in a view-model hook is ceremony." | View-model hooks isolate query composition from rendering. Calling `useQuery` inline couples the view to API shape and re-fetch logic. Compose hooks in `hooks/use-<feature>-<view>-view-model.ts`. |
| "I'll throw an `axios` call in the view-model for a one-off endpoint." | View-models compose shared API hooks only. Raw axios calls belong in `@/api/v1/...` or `@/hooks/api`. The view-model wires those hooks to view-shaped data. |

# Soft rules (warnings, not errors)

The conformance script issues warnings — not blocking failures — for the following. They're still wrong; the script just keeps the gate clean for the worse offenses.

- **`self-barrel-absolute-import`** — Importing your own feature's barrel (`@/features/<g>/<f>`) from inside the feature. Use relative imports within a feature.
- **`self-deep-absolute-import`** — Absolute deep imports into your own feature (`@/features/<g>/<f>/components/Foo`) from inside the feature. Use relative.
- **`feature-root-stray-file`** — Any file at the feature root other than `index.ts` (or `README.md`). Move it into one of the allowed subfolders.

# Migrating a legacy page into a feature

See [legacy-page-to-feature.md](legacy-page-to-feature.md) for the step-by-step recipe (9 steps), the anti-rationalization table (excuses you'll be tempted to make), and the evidence-of-completion checklist.

# Evidence (how to know you're done)

Always before opening or pushing to a PR:

1. `mise exec -- pnpm run check:bulletproof-react` — must output "✓ ... no violations".
2. `mise exec -- pnpm run check` — runs typecheck → prettier → knip → bulletproof. Must pass.
3. Manual smoke-test the affected route in the dev server. Each tab/view renders; loading and error states display correctly.

The conformance script (`web-app/scripts/check-bulletproof-react.mjs`) is the mechanical enforcer. It scans every feature and flags violations of the structural rules above. It is tool-agnostic — runs the same whether the change came from Cursor, Claude Code, or a human.
