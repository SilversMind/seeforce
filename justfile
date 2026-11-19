set dotenv-load := true
set dotenv-path := "backend/.env"

# Rescan a repo's annotations into its .seeforce/workspace.json (defaults to this repo)
scan path=".":
    uv run seeforce scan {{path}}

# Start the Django backend dev server
backend:
    cd backend && uv run python3 manage.py runserver

# Start the Vite frontend dev server
frontend:
    cd frontend && npm run dev

# Rescan workspace.json on every commit (Claude sessions turn this on by themselves)
hooks:
    git config core.hooksPath .githooks
