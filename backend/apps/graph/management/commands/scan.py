import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.graph.models import ProjectMap
from c4parser import scan, build, export_workspace
from c4parser.exceptions import C4ParseError, C4ValidationError

import json

_C4PROJECT_FILE = ".c4project"


def _get_or_create_project_id(paths: list[Path]) -> str:
    """Read project_id from first .c4project found across paths, creating in paths[0] if none exist."""
    for p in paths:
        c4file = p / _C4PROJECT_FILE
        if c4file.exists():
            pid = c4file.read_text(encoding="utf-8").strip()
            if pid:
                return pid
    pid = str(uuid.uuid4())
    (paths[0] / _C4PROJECT_FILE).write_text(pid, encoding="utf-8")
    return pid


class Command(BaseCommand):
    help = "Scan one or more repositories for C4 annotations and upsert the ProjectMap"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            action="append",
            dest="paths",
            metavar="PATH",
            help="Path to a repository root (repeat for multi-repo projects)",
        )
        parser.add_argument("--name", default=None, help="Project name (defaults to first repo folder name)")
        parser.add_argument("--output", default=None, help="Also write workspace.json to this file")

    def handle(self, *args, **options):
        paths = [Path(p).resolve() for p in options["paths"]]
        for p in paths:
            if not p.is_dir():
                raise CommandError(f"'{p}' is not a directory")

        name = options["name"] or paths[0].name
        project_id = _get_or_create_project_id(paths)

        self.stdout.write(f"Scanning {', '.join(str(p) for p in paths)} (project: {project_id[:8]}…)")
        try:
            elements = []
            for p in paths:
                elements.extend(scan(str(p)))
            workspace = build(elements)
            json_str = export_workspace(workspace)
        except C4ParseError as exc:
            raise CommandError(f"Parse error: {exc}")
        except C4ValidationError as exc:
            raise CommandError(f"Validation error: {exc}")

        systems = len(
            [s for s in workspace["model"]["softwareSystems"] if "External" not in s.get("tags", "")]
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

        source_json = json.loads(json_str)
        pm, created = ProjectMap.objects.update_or_create(
            project_id=project_id,
            defaults={"name": name, "source_json": source_json},
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} ProjectMap id={pm.id} '{pm.name}'"))

        if output := options.get("output"):
            Path(output).write_text(json_str, encoding="utf-8")
            self.stdout.write(f"Also saved to {output}")
