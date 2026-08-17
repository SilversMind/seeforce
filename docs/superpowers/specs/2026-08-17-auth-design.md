# Auth & Project Ownership — Design Spec

## Context

SeeForce needs authentication to support multi-user access with ownership-based write permissions. All authenticated users can read any project; only the project owner (first scanner) can write overlays, lexicon entries, or delete the project.

## Auth Strategy

GitHub OAuth via `django-allauth`. Session-based auth with an HttpOnly cookie — no JWT, no token management on the frontend. Works on the same domain for both local dev (localhost) and production.

**Package:** `django-allauth[socialaccount]`

**Environment variables (per environment):**
```
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

**GitHub OAuth App setup:** one app per environment (local: `localhost:8000` callback, prod: real domain callback).

## Data Model

### ProjectMap additions

```python
owner      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="projects")
visibility = models.CharField(max_length=16, default="public")  # reserved for v2
```

- `owner = null` for projects created before auth was introduced — stays null until rescanned
- On scan: if `owner` is null → assign `request.user`. If already set → do not change (first scanner keeps ownership)
- `visibility` is stored but unused in v1. Values: `"public"` (default) | `"private"` (v2: repo-private, invite-only)

### Migration

`0005_projectmap_owner_visibility.py` — adds both fields, nullable, with defaults.

## Permission Rules

| Action | Required |
|--------|----------|
| Read graph / list projects | Authenticated |
| Scan (create or update project) | Authenticated |
| Write node/edge overlay | Authenticated + `request.user == project.owner` |
| Write lexicon entry | Authenticated + `request.user == project.owner` |
| Delete project | Authenticated + `request.user == project.owner` |

Non-owner write attempts return **403 Forbidden**.

Unauthenticated requests return **401 Unauthorized** on all API endpoints.

## Backend

### Django settings additions

```python
INSTALLED_APPS += [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
]
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
SOCIALACCOUNT_PROVIDERS = {
    "github": {"SCOPE": ["user:email"]}
}
LOGIN_REDIRECT_URL = "/"
ACCOUNT_EMAIL_REQUIRED = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
MIDDLEWARE += ["allauth.account.middleware.AccountMiddleware"]
```

### New API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/auth/me/` | optional | Returns `{id, username, avatar_url}` or 401 |
| POST | `/api/auth/logout/` | required | Clears session, returns 200 |
| GET | `/accounts/github/login/` | — | Handled by allauth — redirects to GitHub OAuth |
| GET | `/accounts/github/login/callback/` | — | Handled by allauth — sets cookie, redirects to `/` |

### Existing endpoint changes

- All graph/project endpoints: add `@login_required` (or `IsAuthenticated` check)
- Write endpoints (overlays, lexicon, delete): add owner check → 403 if `request.user != project.owner`
- `GET /api/projects/` response: add `is_mine: bool` and `owner_username: str | null` per project
- Scan command: after `get_or_create` on ProjectMap, assign `owner = request.user` if currently null

### URL routing additions

```python
# urls.py (project root)
path("accounts/", include("allauth.urls")),
path("api/auth/", include("apps.graph.auth_urls")),
```

`auth_urls.py`:
```python
path("me/", views.auth_me),
path("logout/", views.auth_logout),
```

## Frontend

### AuthContext (`src/contexts/AuthContext.tsx`)

```typescript
interface AuthUser { id: number; username: string; avatar_url: string }
interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  logout: () => void;
}
```

- Fetches `/api/auth/me/` via SWR on startup
- If 401 → `user = null`
- `logout()` → POST `/api/auth/logout/` + SWR mutate → clears user

### App routing

`App.tsx` wraps everything in `<AuthProvider>`:
- `isLoading = true` → full-page spinner
- `user = null` → render `<LoginPage>` (replaces all routes)
- `user` set → render normal routes (HomePage, GraphView, etc.)

No public routes in v1 — all content requires auth.

### LoginPage (`src/pages/LoginPage.tsx`)

Minimal: SeeForce logo + tagline + single button:
```
"Se connecter avec GitHub" → href="http://localhost:8000/accounts/github/login/"
```
URL is configurable via `VITE_BACKEND_URL` env var so it works in both local and prod.

### api.ts additions

```typescript
export interface AuthUser { id: number; username: string; avatar_url: string }
export async function fetchMe(): Promise<AuthUser>        // GET /api/auth/me/
export async function logout(): Promise<void>             // POST /api/auth/logout/
```

### ProjectMap API response additions

```typescript
// Added to existing ProjectMapMeta interface:
is_mine: boolean;
owner_username: string | null;
```

### HomePage changes

Projects list split into two sections based on `is_mine`:
- **"Mes projets"** — cards with Edit name + Delete buttons
- **"Projets partagés"** — cards with owner badge (`owner_username`), no edit/delete controls

If `is_mine = false` and `owner = null` (legacy orphan) → shown in "Projets partagés" with no owner badge.

### OverlaySidebar / graph write controls

New prop `isOwner: boolean` passed from `GraphView` → `C4Graph` → `OverlaySidebar`:
- `isOwner = false` → Edit button hidden, lexicon add/delete form hidden
- Read-only display of overlays and lexicon still visible to non-owners

`GraphView` derives `isOwner` from the project's `is_mine` field.

## Data migration

Existing `ProjectMap` rows: `owner = null, visibility = "public"`. No data loss. They appear in all users' "Projets partagés" until rescanned by an authenticated user.

## Out of scope (v1)

- Google / GitLab OAuth
- Role system (contributor, admin)
- Project invite mechanism
- Private projects (`visibility = "private"`)
- User profile page
- Admin panel for managing users
