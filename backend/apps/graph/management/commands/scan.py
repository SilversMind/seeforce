import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.graph.models import ProjectMap
from c4parser import scan, build, export_workspace
from c4parser.exceptions import C4ParseError, C4ValidationError

import json

_SEEFORCE_DIR = ".seeforce"


def _get_or_create_project_id(paths: list[Path]) -> str:
    """Read project_id from .seeforce/project.json, creating it if none exist."""
    for p in paths:
        seeforce_cfg = p / _SEEFORCE_DIR / "project.json"
        if seeforce_cfg.exists():
            import json as _json
            pid = _json.loads(seeforce_cfg.read_text(encoding="utf-8")).get("project_id", "")
            if pid:
                return pid
    pid = str(uuid.uuid4())
    seeforce_dir = paths[0] / _SEEFORCE_DIR
    seeforce_dir.mkdir(exist_ok=True)
    import json as _json
    (seeforce_dir / "project.json").write_text(
        _json.dumps({"project_id": pid}, indent=2), encoding="utf-8"
    )
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
        parser.add_argument(
            "--output",
            default=None,
            help="Write workspace.json here (default: <first-path>/.seeforce/workspace.json, pass 'none' to skip)",
        )
        parser.add_argument(
            "--user-email",
            default=None,
            help="Email of the user to assign as project owner (if not already set)",
        )

    def handle(self, *args, **options):
        paths = [Path(p).resolve() for p in options["paths"]]
        for p in paths:
            if not p.is_dir():
                raise CommandError(f"'{p}' is not a directory")

        name = options["name"] or paths[0].name
        project_id = _get_or_create_project_id(paths)

        user_email = options.get("user_email")
        owner = None
        if user_email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner = User.objects.filter(email=user_email).first()
            if not owner:
                self.stderr.write(self.style.WARNING(
                    f"No user found with email '{user_email}' — owner not assigned"
                ))

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

        if owner is not None and pm.owner is None:
            pm.owner = owner
            pm.save(update_fields=["owner"])
            self.stdout.write(self.style.SUCCESS(f"Assigned owner: {owner.username}"))

        output = options.get("output")
        if output is None:
            output = str(paths[0] / _SEEFORCE_DIR / "workspace.json")
        if output.lower() != "none":
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json_str, encoding="utf-8")
            self.stdout.write(f"Workspace written to {out_path}")
