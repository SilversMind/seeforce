# Homepage — Project Listing

**Date:** 2026-08-05
**Status:** Approved

## Goal

Replace the current single-view app (direct render of GraphView) with a proper two-route app: a homepage listing all projects as cards, and a project view at `/project/:id`.

No auth for this phase. All projects visible to all users.

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `HomePage` | Grid of project cards |
| `/project/:id` | `GraphView` | Existing C4 viewer |

Navigation via `react-router-dom`.

## Backend

**New endpoint:** `GET /api/graph/`

Returns all `ProjectMap` ordered by `updated_at` desc (already the model default).

Response:
```json
[
  { "id": 1, "name": "MyApp", "project_id": "myapp", "updated_at": "2026-08-04T..." },
  ...
]
```

Serializer already has these fields — use existing `ProjectMapSerializer` or a lightweight list serializer.

## Frontend

### New file: `src/pages/HomePage.tsx`

- Header: identical to GraphView header (`#0f172a`, "SeeForce" logo, 48px height)
- Button "+ New project" top-right → navigates to `/project/new` (upload flow)
- Grid: 3 columns max, responsive (`auto-fill`, `minmax(240px, 1fr)`)
- Each card: `background: var(--c4-sidebar-bg)`, `border: 1px solid var(--c4-sidebar-border)`, `borderRadius: 8`, cursor pointer
  - Project name: `var(--c4-sidebar-text)`, 14px, bold
  - Last updated: `var(--c4-sidebar-muted)`, 12px, relative date (e.g. "3 days ago")
  - Click → `navigate(/project/:id)`
- Empty state: centered message "No projects yet. Scan a codebase to get started."
- Data fetched with SWR (`fetchProjectMaps`)

### Modified: `src/App.tsx`

Wrap with `BrowserRouter`, add `Routes` with two `Route` entries.

### Modified: `src/pages/GraphView.tsx`

Read `projectMapId` from `useParams()` instead of from Zustand store / `fetchLatestProjectMap`. SSE listener stays — on `scan_complete`, redirect to `/project/:new_id`.

Route `/project/new` shows `UploadPanel` directly (no graph).

### Modified: `src/services/api.ts`

Add `fetchProjectMaps(): Promise<ProjectMapMeta[]>` — `GET /api/graph/`.

## Styling constraints

- Inline styles only (no CSS classes, consistent with existing codebase)
- All colors via existing CSS variables from `index.css`
- Dark mode: automatic via `prefers-color-scheme` (already handled by CSS vars)
- Border-radius: 8px for cards, 6px for buttons (consistent with existing nodes/buttons)

## Out of scope

- Delete / rename project from homepage
- Search / filter
- Auth / user-scoped projects (next phase)
- Pagination
