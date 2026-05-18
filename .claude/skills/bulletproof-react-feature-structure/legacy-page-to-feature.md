# Migrating an existing page into a feature

Companion to `SKILL.md`. That file covers the **target shape**; this file covers the **how-to-get-there**.

Reference end-state: `web-app/src/features/performance/met-station/` plus the shim at `web-app/src/pages/projects/equipment_analysis/met_station/page.tsx`.

# When to use

- Refactoring a legacy `pages/.../page.tsx` into a feature.
- Splitting a single large page component into route + views + hooks.
- Moving inline fetchers into the shared `@/api/v1/...` layer.

# Inputs to confirm before starting

- The legacy page path.
- Target group (`performance/`, `maintenance/`, …) and feature name (kebab-case).
- Routes that import the legacy page (the shim must keep them working).
- Whether the page has tabs (drives view splitting + `use<Feature>Tab` hook).

# Recipe

1. **Pick the destination.** `web-app/src/features/<group>/<feature>/`. Add a new group only if no existing one fits.
2. **Scaffold only what you need.** Choose from the allowed seven: `components/`, `hooks/`, `queries/`, `routes/`, `types/`, `utils/`, `views/`. Skip any you don't need.
3. **Extract the context hook.** Pull the page's top-level data fetching into `hooks/use-<feature>-context.ts`. It returns `{ <ids>, <entities>, isLoading, error }`. The route checks `isLoading`/`error` once.
4. **Split per view.** For each tab or major section, extract:
   - `hooks/use-<feature>-<view>-view-model.ts` — takes `{ context, ...viewParams }`, returns the shape that view needs. Composes shared API hooks; no axios calls.
   - `views/<View>.tsx` — receives `{ context }` (and other props), calls the view-model hook, renders. PascalCase filename matches the exported component.
5. **Relocate the rest.** Sub-components used only inside the feature → `components/`. Pure helpers → `utils/` (kebab-case). Types → `types/<feature>.ts`.
6. **Wire the route.** Create `routes/<Feature>Route.tsx`. It owns: context hook, loading/error gates, tab state (via `use<Feature>Tab` if applicable), and the conditional view rendering.
7. **Public API.** Add `index.ts` that re-exports only the route component:
   `export { <Feature>Route } from './routes/<Feature>Route'`
8. **Shim the legacy page.** Replace the body of the original `pages/.../page.tsx` with:
   ```tsx
   import { <Feature>Route } from '@/features/<group>/<feature>'

   export default function Page() {
     return <<Feature>Route />
   }
   ```
   This keeps `App.tsx` route definitions untouched.
9. **Verify.** Run `mise exec -- pnpm run check` (typecheck + prettier + knip + bulletproof-react conformance). Open the affected route in the dev server and exercise each tab/view. Confirm the shim's import resolves.

# Common excuses (and the rebuttals)

| Excuse | Rebuttal |
| --- | --- |
| "The legacy page is small — just move it as one component." | If it has tabs or distinct visual sections, it has views. The pattern is the same regardless of size. |
| "I'll inline the fetcher just for now." | The fetcher belongs in `@/api/v1/...` or `@/hooks/api`. Inlining now means another refactor later. Do it once. |
| "The page imports from another feature — I'll keep that import." | No cross-feature imports. Lift the shared piece up to `web-app/src/components/` or `web-app/src/hooks/` first, then migrate. |
| "Adding `index.ts` is overhead." | The barrel is the only public boundary. Without it, callers reach into internals and the boundary erodes. |
| "I'll skip the shim and update `App.tsx` instead." | The shim limits the blast radius. Router edits change every reviewer's mental map of routing; shim edits don't. |
| "I'll just use a side-effect import for the cross-feature dependency." | Any cross-feature import is a no-go (absolute, relative, side-effect). Lift the shared piece to `web-app/src/`. |
| "I'll gate the whole view on `isLoading`." | Per-card `<Skeleton>` keeps the layout stable and shows partial data sooner. Gate the route, not the view. |

# Evidence the conversion is done

- `mise exec -- pnpm run check:bulletproof-react` outputs "✓ ... no violations".
- `mise exec -- pnpm run check` passes (typecheck + prettier + knip + bulletproof).
- The legacy `pages/.../page.tsx` is the one-line shim.
- The new feature has `index.ts` exporting only the route.
- No subfolders outside the allowed seven.
- No imports from other features in any form (absolute, relative, side-effect). The conformance script catches all three.
- Manual smoke-test: each tab/view renders; loading and error states display correctly.
