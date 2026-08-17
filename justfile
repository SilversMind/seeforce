# Run the C4 scanner on one or more project paths (defaults to repo root)
# Single repo:  just scan path/to/project
# Multi-repo:   just scan path/to/backend path/to/frontend
# With owner:   just scan path/to/project user=me@example.com
scan *paths user="":
    #!/usr/bin/env bash
    set -euo pipefail
    root={{justfile_directory()}}
    args=""
    for p in {{paths}}; do
        if [[ "$p" = /* ]]; then
            args="$args --path $p"
        else
            args="$args --path $root/$p"
        fi
    done
    if [ -z "$args" ]; then
        args="--path $root"
    fi
    if [ -n "{{user}}" ]; then
        args="$args --user-email {{user}}"
    fi
    cd backend && uv run python3 manage.py scan $args

# Annotate a codebase with C4 markers using Claude (add --dry-run to preview)
# Single repo:  just annotate path/to/project
# Multi-repo:   just annotate path/to/backend path/to/frontend
annotate *paths:
    #!/usr/bin/env bash
    set -euo pipefail
    root={{justfile_directory()}}
    args=""
    for p in {{paths}}; do
        if [[ "$p" = /* ]]; then
            args="$args --path $p"
        else
            args="$args --path $root/$p"
        fi
    done
    if [ -z "$args" ]; then
        echo "Usage: just annotate <path> [<path2> ...]"
        exit 1
    fi
    cd backend && uv run python3 ../scripts/annotate.py $args

# Start the Django backend dev server
backend:
    cd backend && uv run python3 manage.py runserver

# Start the Vite frontend dev server
frontend:
    cd frontend && npm run dev
