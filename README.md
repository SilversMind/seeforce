# SeeForce

**Visualize your codebase architecture from source code annotations.**

SeeForce scans your code for C4 model annotations and generates an interactive architecture diagram — systems, containers, components, and their relationships — directly from the code, so it never gets out of sync.

Live instance: [seeforce.onrender.com](https://seeforce.onrender.com)

---

## How it works

1. **Annotate** your code with `@c1:system`, `@c2:container`, `@c3:component` markers
2. **Scan** your repo locally → generates `.seeforce/workspace.json`
3. **Import** into SeeForce (upload the file or import from GitHub)

---

## Scanning a project

From this repo root, use `just scan`:

```bash
# Scan the current repo
just scan

# Scan a specific project
just scan ../path/to/project

# Scan multiple repos that share a C4 model (e.g. backend + frontend)
just scan ../my-backend ../my-frontend
```

Output: `.seeforce/workspace.json` in the first scanned path. Commit it to your repo.

### Annotation format

```python
"""
@c1:system
name: My System
description: Does something useful.
"""

"""
@c2:container
name: API Server
system: My System
technology: Python / Django
description: Handles HTTP requests.
"""

"""
@c3:component
name: Auth Service
container: API Server
description: Manages login and sessions.
uses:
  - Database: "reads user records"
    technology: PostgreSQL
"""
```

Supported languages: Python, TypeScript, JavaScript, Go, Rust, Java, C#, Ruby.

---

## Importing into SeeForce

**Upload:** click `+ New project` → `Upload file` → select `.seeforce/workspace.json`

**GitHub import:** click `+ New project` → `Import from GitHub` → enter `owner/repo` and branch. The repo must contain a `.seeforce/workspace.json` (run `just scan` first and commit it).

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Django + Django REST Framework |
| Auth | django-allauth (GitHub OAuth) |
| Frontend | React + React Flow + ELK layout |
| DB | PostgreSQL |
| Deploy | Render |

---

## Development

**Requirements:** Python 3.12+, Node 18+, [uv](https://github.com/astral-sh/uv), [just](https://github.com/casey/just)

```bash
# Backend
cd backend && uv sync && uv run python manage.py migrate && uv run python manage.py runserver

# Frontend
cd frontend && npm install && npm run dev
```

Or with just:

```bash
just backend   # Django dev server on :8000
just frontend  # Vite dev server on :3000
```

## Contributing

Pull requests are welcome. Commits must be signed off (`git commit -s`) — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

Source available under the [Functional Source License 1.1, Apache 2.0 future
license](LICENSE) (FSL-1.1-ALv2). Use it, modify it, self-host it, including
commercially inside your own company. The one thing you may not do is offer
SeeForce, or something substantially similar, as a competing product or
service. Every release turns into Apache-2.0 two years after it ships.
