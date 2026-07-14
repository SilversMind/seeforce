from dataclasses import dataclass, field


@dataclass
class C4System:
    name: str
    description: str = ""
    external: bool = False
    source_file: str = ""


@dataclass
class C4Container:
    name: str
    system: str
    technology: str = ""
    description: str = ""
    uses: list[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class C4Component:
    name: str
    container: str
    technology: str = ""
    description: str = ""
    uses: list[str] = field(default_factory=list)
    source_file: str = ""


C4Element = C4System | C4Container | C4Component
