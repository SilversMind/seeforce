# Homepage Project Listing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a homepage listing all projects as clickable cards, routed via react-router-dom, backed by a new Django list endpoint.

**Architecture:** Add `GET /api/graph/` backend endpoint; install react-router-dom and wire two routes (`/` → HomePage, `/project/:id` → GraphView); new HomePage component fetches project list via SWR and renders cards; GraphView reads project ID from URL params instead of Zustand store.

**Tech Stack:** Django REST Framework (backend), React 19, react-router-dom v7, SWR, Zustand, TypeScript, Vite (frontend)

## Global Constraints

- Inline styles only — no CSS classes added
- All colors via existing CSS variables defined in `frontend/src/index.css`
- Dark mode automatic via `prefers-color-scheme` (CSS vars already handle it)
- Border-radius: 8px for cards, 6px for buttons
- Backend tests use Django `TestCase` (not pytest-django fixtures)
- Working directory for backend commands: `/Users/bouzdi/Dev/c4/backend`
- Working directory for frontend commands: `/Users/bouzdi/Dev/c4/frontend`

---

### Task 1: Backend list endpoint + fix broken test import

**Files:**
- Modify: `backend/apps/graph/views.py` — add `list_project_maps` view
- Modify: `backend/apps/graph/urls.py` — add route for listing
- Modify: `backend/tests/graph/test_views.py` — fix `Workspace` → `ProjectMap` import + add list test

**Interfaces:**
- Produces: `GET /api/graph/` → `[{id, name, project_id, updated_at}, ...]` ordered by `-updated_at`

- [ ] **Step 1: Fix broken test import**

In `tests/graph/test_views.py`, change line 5:
```python
# from
from apps.graph.models import Workspace
# to
from apps.graph.models import ProjectMap
```
Then replace every `Workspace` reference in that file with `ProjectMap` (appears in `setUp` and `Workspace.objects.create`).

- [ ] **Step 2: Run existing tests to verify they pass now**

```bash
cd /Users/bouzdi/Dev/c4/backend
uv run pytest tests/graph/test_views.py -v
```
Expected: all existing tests pass (no import errors).

- [ ] **Step 3: Write failing test for list endpoint**

Append to `tests/graph/test_views.py`:
```python
class ListProjectMapsTest(TestCase):
    def setUp(self):
        ProjectMap.objects.create(name="Alpha", source_json={})
        ProjectMap.objects.create(name="Beta", source_json={})

    def test_list_returns_all_projects(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        names = {p["name"] for p in data}
        self.assertIn("Alpha", names)
        self.assertIn("Beta", names)

    def test_list_contains_required_fields(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        for field in ("id", "name", "project_id", "updated_at"):
            self.assertIn(field, item)

    def test_list_ordered_by_updated_at_desc(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]["name"], "Beta")  # created last = updated_at newest
```

- [ ] **Step 4: Run to verify it fails**

```bash
uv run pytest tests/graph/test_views.py::ListProjectMapsTest -v
```
Expected: FAIL with 404 (route not wired yet).

- [ ] **Step 5: Add list view to views.py**

In `backend/apps/graph/views.py`, add after the imports:
```python
@api_view(["GET"])
def list_project_maps(request):
    pms = ProjectMap.objects.all()
    return Response([
        {"id": pm.id, "name": pm.name, "project_id": pm.project_id, "updated_at": pm.updated_at}
        for pm in pms
    ])
```

- [ ] **Step 6: Wire URL in urls.py**

In `backend/apps/graph/urls.py`, add as first entry:
```python
path("", views.list_project_maps),
```
Full urlpatterns:
```python
urlpatterns = [
    path("", views.list_project_maps),
    path("upload/", views.upload_project_map),
    path("latest/", views.latest_project_map),
    path("events/", views.scan_events),
    path("<int:project_map_id>/", views.fetch_project_map),
    path("<int:project_map_id>/view/<str:level>/", views.project_map_view),
    path("<int:project_map_id>/overlay/node/", views.upsert_node_overlay),
    path("<int:project_map_id>/overlay/edge/", views.upsert_edge_overlay),
]
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
uv run pytest tests/graph/test_views.py -v
```
Expected: all tests pass including the 3 new list tests.

- [ ] **Step 8: Commit**

```bash
cd /Users/bouzdi/Dev/c4
git add backend/apps/graph/views.py backend/apps/graph/urls.py backend/tests/graph/test_views.py
git commit -m "feat: add GET /api/graph/ list endpoint, fix stale Workspace import in tests"
```

---

### Task 2: Install react-router-dom + add fetchProjectMaps + wire App.tsx

**Files:**
- Modify: `frontend/package.json` — add react-router-dom dependency
- Modify: `frontend/src/services/api.ts` — add `fetchProjectMaps()`
- Modify: `frontend/src/App.tsx` — BrowserRouter + Routes

**Interfaces:**
- Consumes: `GET /api/graph/` (from Task 1)
- Produces:
  - `fetchProjectMaps(): Promise<ProjectMapMeta[]>` exported from `api.ts`
  - Routes: `/` renders `<HomePage />`, `/project/new` renders `<UploadPanel />` in a flex shell, `/project/:id` renders `<GraphView />`

- [ ] **Step 1: Install react-router-dom**

```bash
cd /Users/bouzdi/Dev/c4/frontend
npm install react-router-dom
```
Expected: `package.json` gains `"react-router-dom": "^7.x.x"` in dependencies.

- [ ] **Step 2: Add fetchProjectMaps to api.ts + extend ProjectMapMeta**

In `frontend/src/services/api.ts`, add `updated_at` to the `ProjectMapMeta` interface (line 5):
```typescript
export interface ProjectMapMeta {
  id: number;
  name: string;
  project_id: string | null;
  created_at: string;
  updated_at: string;
}
```

Then add `fetchProjectMaps` after `fetchLatestProjectMap`:
```typescript
export async function fetchProjectMaps(): Promise<ProjectMapMeta[]> {
  const res = await fetch("/api/graph/");
  if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 3: Update App.tsx with router**

Replace `frontend/src/App.tsx` entirely:
```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { GraphView } from "./pages/GraphView";
import { HomePage } from "./pages/HomePage";
import { UploadPanel } from "./components/UploadPanel";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/project/new"
          element={
            <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
              <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", flexShrink: 0 }}>
                <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>SeeForce</span>
              </header>
              <div style={{ flex: 1 }}>
                <UploadPanel />
              </div>
            </div>
          }
        />
        <Route path="/project/:id" element={<GraphView />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /Users/bouzdi/Dev/c4/frontend
npx tsc --noEmit
```
Expected: errors only about missing `HomePage` (not yet created) — that's fine at this stage.

- [ ] **Step 5: Commit**

```bash
cd /Users/bouzdi/Dev/c4
git add frontend/package.json frontend/package-lock.json frontend/src/App.tsx frontend/src/services/api.ts
git commit -m "feat: install react-router-dom, add fetchProjectMaps, wire App routes"
```

---

### Task 3: HomePage component

**Files:**
- Create: `frontend/src/pages/HomePage.tsx`

**Interfaces:**
- Consumes: `fetchProjectMaps(): Promise<ProjectMapMeta[]>` from `../services/api`
- Consumes: `ProjectMapMeta` interface from `../services/api`
- Produces: `<HomePage />` component, exported as named export

- [ ] **Step 1: Create HomePage.tsx**

Create `frontend/src/pages/HomePage.tsx`:
```tsx
import useSWR from "swr";
import { useNavigate } from "react-router-dom";
import { fetchProjectMaps, type ProjectMapMeta } from "../services/api";

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  if (months < 12) return `${months} months ago`;
  return `${Math.floor(months / 12)} years ago`;
}

function ProjectCard({ project, onClick }: { project: ProjectMapMeta; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--c4-sidebar-bg)",
        border: "1px solid var(--c4-sidebar-border)",
        borderRadius: 8,
        padding: 20,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        transition: "border-color 0.15s",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--c4-system-border)")}
      onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--c4-sidebar-border)")}
    >
      <div style={{ fontWeight: 700, fontSize: 14, color: "var(--c4-sidebar-text)" }}>
        {project.name}
      </div>
      <div style={{ fontSize: 12, color: "var(--c4-sidebar-muted)" }}>
        Updated {relativeDate(project.updated_at)}
      </div>
    </div>
  );
}

export function HomePage() {
  const navigate = useNavigate();
  const { data: projects, isLoading, error } = useSWR<ProjectMapMeta[]>(
    "/api/graph/",
    fetchProjectMaps,
  );

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column", background: "var(--c4-page-bg)" }}>
      <header style={{ height: 48, background: "#0f172a", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, flexShrink: 0 }}>
        <span style={{ color: "white", fontWeight: 700, fontSize: 16 }}>SeeForce</span>
        <button
          onClick={() => navigate("/project/new")}
          style={{
            marginLeft: "auto",
            background: "#1e293b",
            color: "#94a3b8",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          + New project
        </button>
      </header>

      <main style={{ flex: 1, padding: 32, overflowY: "auto" }}>
        {isLoading && (
          <div style={{ color: "var(--c4-sidebar-muted)", fontSize: 14 }}>Loading…</div>
        )}
        {error && (
          <div style={{ color: "#ef4444", fontSize: 14 }}>Failed to load projects.</div>
        )}
        {projects && projects.length === 0 && (
          <div style={{ textAlign: "center", color: "var(--c4-sidebar-muted)", fontSize: 14, marginTop: 80 }}>
            No projects yet. Scan a codebase to get started.
          </div>
        )}
        {projects && projects.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 16, maxWidth: 1200 }}>
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} onClick={() => navigate(`/project/${p.id}`)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/bouzdi/Dev/c4/frontend
npx tsc --noEmit
```
Expected: no errors (or only pre-existing ones unrelated to this task).

- [ ] **Step 3: Smoke test in browser**

Start backend and frontend, open `http://localhost:5173/`. Verify:
- Header shows "SeeForce" + "+ New project" button
- Projects list appears (or empty state if no projects in DB)
- Clicking a card navigates to `/project/:id`
- Clicking "+ New project" navigates to `/project/new` (shows UploadPanel)

- [ ] **Step 4: Commit**

```bash
cd /Users/bouzdi/Dev/c4
git add frontend/src/pages/HomePage.tsx
git commit -m "feat: add HomePage with project cards grid"
```

---

### Task 4: Update GraphView + UploadPanel to use router

**Files:**
- Modify: `frontend/src/pages/GraphView.tsx` — read ID from `useParams`, navigate on scan_complete
- Modify: `frontend/src/components/UploadPanel.tsx` — use `useNavigate` instead of `useViewStore.setProjectMap`

**Interfaces:**
- Consumes: `useParams<{ id: string }>()` from react-router-dom — `id` is always a valid numeric string when rendered at `/project/:id`
- Consumes: `useNavigate()` from react-router-dom

- [ ] **Step 1: Update GraphView.tsx**

Replace `frontend/src/pages/GraphView.tsx` entirely:
```tsx
import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { mutate } from "swr";
import { useViewStore } from "../store/viewStore";
import { C4Graph } from "../components/Graph/C4Graph";

export function GraphView() {
  const { id } = useParams<{ id: string }>();
  const projectMapId = parseInt(id!, 10);
  const navigate = useNavigate();

  const setProjectMap = useViewStore((s) => s.setProjectMap);

  useEffect(() => {
    setProjectMap(projectMapId);
  }, [projectMapId, setProjectMap]);

  useEffect(() => {
    const es = new EventSource("/api/graph/events/");

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "scan_complete") {
        mutate((key) => typeof key === "string" && key.includes("/api/graph/"));
        navigate(`/project/${data.id}`);
      }
    };

    es.onerror = () => es.close();
    return () => es.close();
  }, [navigate]);

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          height: 48,
          background: "#0f172a",
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          gap: 12,
          flexShrink: 0,
        }}
      >
        <span
          onClick={() => navigate("/")}
          style={{ color: "white", fontWeight: 700, fontSize: 16, cursor: "pointer" }}
        >
          SeeForce
        </span>
        <button
          onClick={() => navigate("/")}
          style={{
            marginLeft: "auto",
            background: "#1e293b",
            color: "#94a3b8",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "4px 12px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          ← Projects
        </button>
      </header>
      <div style={{ flex: 1 }}>
        <C4Graph />
      </div>
    </div>
  );
}
```

Note: "↺ New project" becomes "← Projects" (navigates back to `/`). UploadPanel removed from GraphView — it now only lives at `/project/new` via App.tsx. `CLEARED_KEY` sessionStorage logic removed (no longer needed with URL-based navigation).

- [ ] **Step 2: Update UploadPanel.tsx**

Replace `setProjectMap` usage with `useNavigate`. Full replacement:
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadProjectMap } from "../services/api";

export function UploadPanel() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const text = await file.text();
      const workspace = JSON.parse(text);
      const name = workspace.name || file.name.replace(".json", "");
      const meta = await uploadProjectMap(name, workspace);
      navigate(`/project/${meta.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16 }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "#0f172a" }}>SeeForce</h2>
      <p style={{ color: "#64748b", fontSize: 14, textAlign: "center", maxWidth: 360 }}>
        Run <code style={{ background: "#f1f5f9", padding: "1px 6px", borderRadius: 4, fontSize: 13 }}>python manage.py scan --path /your/project</code> to auto-load, or upload a workspace.json manually.
      </p>
      <label style={{ cursor: "pointer", background: "#3b82f6", color: "white", padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600 }}>
        {loading ? "Uploading..." : "Choose workspace.json"}
        <input type="file" accept=".json" onChange={handleFile} style={{ display: "none" }} disabled={loading} />
      </label>
      {error && <p style={{ color: "#ef4444", fontSize: 13 }}>{error}</p>}
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/bouzdi/Dev/c4/frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Full smoke test**

Start backend + frontend. Test these flows:
1. Open `http://localhost:5173/` → homepage shows project list
2. Click a project card → navigates to `/project/:id`, C4 graph renders
3. Click "← Projects" in header → back to homepage
4. Click "SeeForce" logo → back to homepage
5. Click "+ New project" on homepage → `/project/new` shows UploadPanel
6. Upload a valid workspace.json → navigates to `/project/:new_id`, graph renders
7. Scan a project via CLI → SSE fires, navigates/refreshes to updated project

- [ ] **Step 5: Commit**

```bash
cd /Users/bouzdi/Dev/c4
git add frontend/src/pages/GraphView.tsx frontend/src/components/UploadPanel.tsx
git commit -m "feat: update GraphView and UploadPanel to use react-router navigation"
```
