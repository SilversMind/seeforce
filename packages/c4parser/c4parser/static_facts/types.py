from dataclasses import dataclass, field


@dataclass
class ImportFact:
    raw: str
    resolved_path: str | None = None
    kind: str = "internal"  # "internal" | "external_known"


@dataclass
class DefFact:
    name: str
    kind: str  # "function" | "class"
    docstring: str = ""


@dataclass
class FileFacts:
    file: str
    imports: list[ImportFact] = field(default_factory=list)
    defines: list[DefFact] = field(default_factory=list)
