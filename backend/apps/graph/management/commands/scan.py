import json
from pathlib import Path

import requests
from django.core.management.base import BaseCommand, CommandError

from c4parser import scan, build, export_workspace
from c4parser.exceptions import C4ParseError, C4ValidationError


class Command(BaseCommand):
    help = "Scan a repository for @c1:/@c2:/@c3: annotations and generate workspace.json"

    def add_arguments(self, parser):
        parser.add_argument("repo_path", help="Path to the repository root")
        parser.add_argument("--output", help="Write workspace.json to this file")
        parser.add_argument("--upload", help="POST workspace.json to this URL (e.g. http://localhost:8000/api/graph/upload/)")
        parser.add_argument("--name", default=None, help="Workspace name (defaults to repo folder name)")

    def handle(self, *args, **options):
        repo_path = options["repo_path"]
        if not Path(repo_path).is_dir():
            raise CommandError(f"'{repo_path}' is not a directory")

        name = options["name"] or Path(repo_path).name

        self.stdout.write(f"Scanning {repo_path}...")
        try:
            elements = scan(repo_path)
            workspace = build(elements)
            json_str = export_workspace(workspace)
        except C4ParseError as exc:
            raise CommandError(f"Parse error: {exc}")
        except C4ValidationError as exc:
            raise CommandError(f"Validation error: {exc}")

        # Exclude auto-generated external placeholder systems (broker `uses`
        # targets) from the summary — only count annotated elements.
        systems = len(
            [
                s
                for s in workspace["model"]["softwareSystems"]
                if "External" not in s.get("tags", "")
            ]
        )
        containers = sum(len(s.get("containers", [])) for s in workspace["model"]["softwareSystems"])
        components = sum(
            len(c.get("components", []))
            for s in workspace["model"]["softwareSystems"]
            for c in s.get("containers", [])
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Found: {systems} system(s), {containers} container(s), {components} component(s)"
            )
        )

        if output := options.get("output"):
            Path(output).write_text(json_str, encoding="utf-8")
            self.stdout.write(f"Saved to {output}")

        if upload_url := options.get("upload"):
            try:
                resp = requests.post(
                    upload_url,
                    json={"name": name, "workspace": json.loads(json_str)},
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                self.stdout.write(self.style.SUCCESS(f"Uploaded — workspace id: {data['id']}"))
            except Exception as exc:
                raise CommandError(f"Upload failed: {exc}")

        if not options.get("output") and not options.get("upload"):
            self.stdout.write(json_str)
