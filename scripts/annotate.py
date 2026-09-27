#!/usr/bin/env python3
"""
Analyze a codebase with Claude and insert C4 architecture annotations.

Usage:
    python scripts/annotate.py --path /repo [--path /repo2] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic

_REPO_ROOT = Path(__file__).parent.parent

_IGNORE_DIRS = frozenset({
    "node_modules", "__pycache__", ".git", "dist", "build", "vendor",
    ".venv", "venv", ".env", "migrations", ".github", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
})
_SKIP_EXTS = frozenset({
    ".lock", ".svg", ".png", ".jpg", ".jpeg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".pyc",
})
_CODE_EXTS = frozenset({".py", ".ts", ".tsx", ".js", ".jsx"})
_CONFIG_NAMES = frozenset({
    "README.md", "package.json", "pyproject.toml",
    "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile", "Dockerfile.production",
})
_ENTRY_NAMES = frozenset({
    "manage.py", "main.py", "app.py",
    "main.tsx", "main.ts", "App.tsx", "index.ts",
    "settings.py", "urls.py", "asgi.py", "wsgi.py",
    "routes.py", "routing.py",
})
_TEST_DIR_NAMES = frozenset({"tests", "test", "__tests__", "spec"})
_MAX_FILE_CHARS = 40_000


def _is_test_path(rel: str) -> bool:
    parts = Path(rel).parts
    name = Path(rel).name
    return (
        any(p in _TEST_DIR_NAMES for p in parts)
        or name.startswith("test_")
        or name.endswith(("_test.py", ".spec.ts", ".test.ts"))
    )


def collect_files(paths: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}

    for root in paths:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]

            for fname in filenames:
                fpath = Path(dirpath) / fname
                ext = fpath.suffix.lower()

                if ext in _SKIP_EXTS:
                    continue

                rel = str(fpath.relative_to(root))

                is_priority = fpath.name in (_CONFIG_NAMES | _ENTRY_NAMES)
                is_code = ext in _CODE_EXTS and not _is_test_path(rel)

                if not (is_priority or is_code):
                    continue

                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                if len(content) > _MAX_FILE_CHARS:
                    content = content[:_MAX_FILE_CHARS] + "\n... [truncated]"

                result[str(fpath)] = content

    return result


def build_user_message(files: dict[str, str]) -> str:
    parts = [
        (
            "Analyze the following codebase and produce C4 annotations.\n\n"
            "Return a JSON object with EXACTLY this shape — no other text, no markdown wrapper:\n"
            '{"annotations": [{"file": "/absolute/path/to/file", "annotation": "@c2:container\\nname: ..."}]}\n\n'
            "Rules:\n"
            "- Annotate only files that represent a C4 architectural boundary\n"
            "- Prefer __init__.py or module entry points over individual class files\n"
            "- The 'annotation' value is raw YAML starting with @cN:kind — no quotes, no comment markers\n"
            "- Skip test files, migrations, utility helpers with no architectural significance\n"
            "- One annotation per file maximum\n\n"
            "Files:\n"
        )
    ]
    for path, content in sorted(files.items()):
        parts.append(f"\n### {path}\n```\n{content}\n```\n")
    return "".join(parts)


def insert_annotation(file_path: Path, annotation: str) -> bool:
    try:
        original = file_path.read_text(encoding="utf-8")
    except OSError:
        return False

    if "@c1:" in original or "@c2:" in original or "@c3:" in original:
        print("  (skipped — already annotated)")
        return False

    ext = file_path.suffix.lower()
    if ext == ".py":
        block = f'"""\n{annotation.strip()}\n"""\n'
    elif ext in {".ts", ".tsx", ".js", ".jsx"}:
        block = f"/*\n{annotation.strip()}\n*/\n"
    else:
        print("  (skipped — unsupported file type)")
        return False

    file_path.write_text(block + original, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Add C4 annotations using Claude")
    parser.add_argument("--path", action="append", dest="paths", required=True, metavar="PATH")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without modifying files")
    parser.add_argument("--model", default="claude-opus-4-8", help="Claude model ID")
    args = parser.parse_args()

    paths = [Path(p).resolve() for p in args.paths]
    for p in paths:
        if not p.is_dir():
            print(f"Error: '{p}' is not a directory", file=sys.stderr)
            sys.exit(1)

    prompt_file = _REPO_ROOT / "prompts" / "c4_annotator.md"
    if not prompt_file.exists():
        print(f"Error: prompt not found at {prompt_file}", file=sys.stderr)
        sys.exit(1)

    system_prompt = prompt_file.read_text(encoding="utf-8")

    print(f"Collecting files from: {', '.join(str(p) for p in paths)}")
    files = collect_files(paths)
    print(f"Collected {len(files)} files")

    client = anthropic.Anthropic()
    print(f"Calling {args.model}…")

    message = client.messages.create(
        model=args.model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": build_user_message(files)}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fence if present
    for fence in ("```json", "```"):
        if raw.startswith(fence):
            raw = raw[len(fence):].lstrip()
            if "```" in raw:
                raw = raw[: raw.index("```")]
            break

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: could not parse response as JSON: {exc}", file=sys.stderr)
        print("Raw (first 500 chars):", raw[:500], file=sys.stderr)
        sys.exit(1)

    annotations = result.get("annotations", [])
    print(f"\nLLM produced {len(annotations)} annotation(s)\n")

    modified = 0
    for item in annotations:
        file_path = Path(item["file"])
        annotation = item["annotation"]
        first_line = annotation.splitlines()[0] if annotation else ""

        prefix = "[DRY-RUN] " if args.dry_run else ""
        print(f"{prefix}→ {file_path}")
        print(f"  {first_line}")

        if not args.dry_run and insert_annotation(file_path, annotation):
            modified += 1

    if args.dry_run:
        print(f"\n{len(annotations)} annotation(s) would be written (dry-run, no files changed)")
    else:
        print(f"\nDone. {modified} file(s) annotated.")
        print("Run 'just scan' to update the project map.")


if __name__ == "__main__":
    main()
