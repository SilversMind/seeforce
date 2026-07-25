# Run the C4 scanner on a project path (defaults to repo root)
scan path=".":
    cd backend && uv run python3 manage.py scan --path {{justfile_directory()}}/{{path}}

# Start the Django backend dev server
backend:
    cd backend && uv run python3 manage.py runserver

# Start the Vite frontend dev server
frontend:
    cd frontend && npm run dev
