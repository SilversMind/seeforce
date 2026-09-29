from dataclasses import dataclass, field


@dataclass
class C4System:
    name: str
    description: str = ""
    short_desc: str = ""
    external: bool = False
    source_file: str = ""


@dataclass
class C4Person:
    """A human role that interacts with the system, rendered at C1.

    `uses` names the systems this role interacts with, not containers: C1 shows
    systems, so a container target would produce an edge with no node to land on.
    """
    name: str
    description: str = ""
    short_desc: str = ""
    uses: list[str | dict[str, str]] = field(default_factory=list)
    source_file: str = ""


@dataclass
class C4Container:
    name: str
    system: str
    technology: str = ""
    description: str = ""
    short_desc: str = ""
    uses: list[str | dict[str, str]] = field(default_factory=list)
    source_file: str = ""


@dataclass
class C4Component:
    name: str
    container: str
    technology: str = ""
    description: str = ""
    short_desc: str = ""
    uses: list[str | dict[str, str]] = field(default_factory=list)
    source_file: str = ""


@dataclass
class C4Lexicon:
    term: str
    definition: str
    source_file: str = ""


C4Element = C4System | C4Person | C4Container | C4Component | C4Lexicon
