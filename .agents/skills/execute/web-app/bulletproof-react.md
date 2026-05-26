# Bulletproof React Feature Structure Specification

This document defines the condensed architectural rules for adding, refactoring, or managing features under `web-app/src/features/`. Conformance is strictly enforced via `pnpm check:bulletproof-react`.

---

## Folder Layout & Naming
Features live under `web-app/src/features/<group>/<feature>/` (e.g., `performance/met-station/`). Feature folders must be **kebab-case**.

**Allowed subfolders** (any others will fail the conformance check):
- `components` — Feature-specific presentational and composite UI components
- `hooks` — React hooks (state, wiring, context consumers)
- `queries` — Feature-local data hooks (use sparingly)
- `routes` — Route-level entry components
- `types` — TypeScript type definitions
- `utils` — Pure helpers, builders, and normalizers
- `views` — Major screens or tab panels composed from local components

**Naming Conventions:**
- **PascalCase `.tsx`**: Used when the file's primary export is a React component. The primary symbol must match the filename (e.g., `MetStationRoute.tsx`, `DayView.tsx`).
- **kebab-case `.ts`**: Used for all non-component files (e.g., `build-time-search-params.ts`).
- **Hooks & Queries**: Files inside `hooks/` and `queries/` must follow the `use-<kebab>.ts` pattern.

---

## Public API & Imports
- **No Root Barrels**: Feature root `index.ts` files are forbidden.
- **Internal Imports**: Files within a feature must use **relative paths** (e.g., `../components/Tabs`). Do not use absolute aliases (`@/features/...`) to point inside the current feature.
- **External Imports**: Outside callers can **only** import route entry components from `@/features/<group>/<feature>/routes/<Feature>Route`.
- **Cross-Feature Imports Forbidden**: Features are strictly prohibited from importing from other features in any form (absolute, relative, or side-effect). Cross-cutting logic must be lifted to shared global directories (`@/components/`, `@/hooks/`, or `@/lib/`).

---

## Data Layer & Hooks Pattern
Do not execute raw `axios` calls or place inline `useQuery` invocations directly inside views. Query hooks belong in shared locations (`@/api/v1/...` or `@/hooks/api`). 

Features utilize a strict two-tier hook pattern:
1. **Context Hook** (`hooks/use-<feature>-context.ts`): Aggregates all query and global state needed by the feature. Returns `{ isLoading, error, data }`, checked once at the route boundary.
2. **View-Model Hook** (`hooks/use-<feature>-<view>-view-model.ts`): One per view. Composes context data and global hooks into the specific shape required for presentation.

```tsx
// routes/FeatureRoute.tsx
function FeatureRoute() {
  const context = useFeatureContext({ projectId })
  if (context.isLoading) return <PageLoader />
  if (context.error !== null) return <PageError text="..." />
  return <Tabs>{activeTab === 'x' && <XView context={context} />}</Tabs>
}

// views/XView.tsx
function XView({ context }: { context: FeatureContext }) {
  const data = useFeatureXViewModel({ context, ...params })
  return <Layout>...</Layout>
}
