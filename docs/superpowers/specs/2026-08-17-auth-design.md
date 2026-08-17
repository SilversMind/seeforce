# Auth & Project Ownership — Design Spec

## Context

SeeForce needs authentication so each user sees only their own projects. The project owner (first scanner) is the sole writer — no shared projects in v1.

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
| List / read own projects | Authenticated |
| Scan (create or update project) | Authenticated |
| Write node/edge overlay | Authenticated + `request.user == project.owner` |
| Write lexicon entry | Authenticated + `request.user == project.owner` |
| Delete project | Authenticated + `request.user == project.owner` |

Projects are filtered by owner — users only see their own projects. Legacy projects (`owner = null`) are visible to the first user who rescans them; until then they are not listed.

Non-owner access attempts return **403 Forbidden**.

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
- `GET /api/projects/` filters by `owner = request.user` — no `is_mine` / `owner_username` fields needed
- Write endpoints (overlays, lexicon, delete): add owner check → 403 if `request.user != project.owner`
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

### HomePage changes

No structural change — single list of projects (all owned by the current user). Edit name + Delete buttons remain as-is.

### OverlaySidebar / graph write controls

No change needed in v1 — all visible projects are owned by the current user, so write controls are always enabled.

## Data migration

Existing `ProjectMap` rows: `owner = null, visibility = "public"`. No data loss. They are not listed in any user's project list until rescanned — at which point the scanning user becomes owner.

## Out of scope (v1)

- Google / GitLab OAuth
- Project sharing / shared projects view
- Role system (contributor, maintainer, viewer)
- Project invite mechanism
- Private projects (`visibility = "private"`)
- User profile page
- Admin panel for managing users
