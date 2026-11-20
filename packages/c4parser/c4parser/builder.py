"""
@c3:component
name: Workspace Builder
container: Annotation Parser
description: |
  - Resolves every uses: reference to an element id
  - Assembles systems, people, containers, components, relationships and views into workspace.json
  - Flags structural drift before the workspace is written:
    - Level-mixing and ambiguous references
    - Orphan elements and containers with no component
    - Unreadable descriptions
  - Weighs each container and component by the lines of code of the files it owns
short_desc: Resolves relationships into workspace.json; the structural drift gate
"""
import re

from .exceptions import C4ValidationError
from .scanner import format_description
from .types import C4Component, C4Container, C4Element, C4Lexicon, C4Person, C4System


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


_EDGE_FIELDS = ("technology", "short_desc")


def _use_name(entry: str | dict) -> str:
    if isinstance(entry, dict):
        return next((k for k in entry if k not in _EDGE_FIELDS), "")
    return entry


def _use_description(entry: str | dict) -> str:
    if isinstance(entry, dict):
        name_key = next((k for k in entry if k not in _EDGE_FIELDS), None)
        return format_description(entry[name_key]) if name_key is not None else ""
    return ""


def _use_short_desc(entry: str | dict) -> str:
    return str(entry.get("short_desc", "")).strip() if isinstance(entry, dict) else ""


def edge_label(rel: dict) -> str:
    """Return the text an edge shows on the canvas: its short_desc, else its flow when it has only one."""
    flows = split_flows(rel.get("description", ""))
    return rel.get("short_desc") or (flows[0] if len(flows) == 1 else "")


def merge_labels(labels: list[str]) -> str:
    """Join the canvas labels of merged edges, each once."""
    return ", ".join(dict.fromkeys(label for label in labels if label))


def split_flows(label: str) -> list[str]:
    """Return the flows an edge label carries, one per `- ` line, or the whole label when it is one phrase."""
    lines = [line.strip() for line in label.splitlines() if line.strip()]
    return [line[2:].strip() if line.startswith("- ") else line for line in lines]


def merge_flows(labels: list[str]) -> str:
    """Merge edge labels into one: a single flow stays a phrase, several become `- ` lines."""
    flows: list[str] = []
    for label in labels:
        flows += [f for f in split_flows(label) if f not in flows]
    return flows[0] if len(flows) == 1 else "\n".join(f"- {f}" for f in flows)


def _parent_dir(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def attribute_lines(
    containers: list[C4Container], components: list[C4Component], line_counts: dict[str, int]
) -> tuple[dict[str, float], dict[tuple[str, str], float]]:
    """Gives each file's lines to the components annotated nearest to it, else to the nearest container."""
    comp_by_file: dict[str, list[C4Component]] = {}
    cont_by_file: dict[str, list[C4Container]] = {}
    comp_by_dir: dict[str, list[C4Component]] = {}
    cont_by_dir: dict[str, list[C4Container]] = {}
    for comp in components:
        comp_by_file.setdefault(comp.source_file, []).append(comp)
        comp_by_dir.setdefault(_parent_dir(comp.source_file), []).append(comp)
    for cont in containers:
        cont_by_file.setdefault(cont.source_file, []).append(cont)
        cont_by_dir.setdefault(_parent_dir(cont.source_file), []).append(cont)

    cont_lines: dict[str, float] = {}
    comp_lines: dict[tuple[str, str], float] = {}

    def give(owners: list, lines: int) -> None:
        # Several components in one file or folder share its lines evenly.
        for owner in owners:
            if isinstance(owner, C4Component):
                key = (owner.container, owner.name)
                comp_lines[key] = comp_lines.get(key, 0) + lines / len(owners)
            else:
                cont_lines[owner.name] = cont_lines.get(owner.name, 0) + lines / len(owners)

    for path, lines in line_counts.items():
        if path in comp_by_file or path in cont_by_file:
            give(comp_by_file.get(path) or cont_by_file[path], lines)
            continue
        folder = _parent_dir(path)
        while True:
            owners = comp_by_dir.get(folder) or cont_by_dir.get(folder)
            if owners:
                give(owners, lines)
                break
            if not folder:
                break
            folder = _parent_dir(folder)
    return cont_lines, comp_lines


def _use_technology(entry: str | dict) -> str:
    if isinstance(entry, dict):
        return entry.get("technology", "")
    return ""


def find_orphans(workspace: dict) -> list[str]:
    """Return warnings for C2/C3 elements with no relationship in either
    direction. A container or component nothing calls and that calls
    nothing isn't doing anything at that level — almost always a missing
    `uses:` annotation, not an intentional design."""
    incoming: set[str] = set()
    for sys_node in workspace["model"]["softwareSystems"]:
        for cont in sys_node.get("containers", []):
            for rel in cont.get("relationships", []):
                incoming.add(rel["destinationId"])
            for comp in cont.get("components", []):
                for rel in comp.get("relationships", []):
                    incoming.add(rel["destinationId"])

    warnings: list[str] = []
    for sys_node in workspace["model"]["softwareSystems"]:
        if "External" in sys_node.get("tags", ""):
            continue
        for cont in sys_node.get("containers", []):
            if not cont.get("relationships") and cont["id"] not in incoming:
                warnings.append(f"Container '{cont['name']}' has no relationships (no uses:, not referenced by anything) — orphan container")
            for comp in cont.get("components", []):
                if not comp.get("relationships") and comp["id"] not in incoming:
                    warnings.append(f"Component '{comp['name']}' (in '{cont['name']}') has no relationships — orphan component")
    return warnings


def find_empty_containers(workspace: dict) -> list[str]:
    """Return warnings for C2 containers with zero C3 components. A container
    worth its own @c2 is worth breaking into at least one @c3 — even a single
    component that just restates the container in more detail. If there's
    nothing to say at the component level, the container likely shouldn't
    have been split out as its own @c2 in the first place."""
    warnings: list[str] = []
    for sys_node in workspace["model"]["softwareSystems"]:
        if "External" in sys_node.get("tags", ""):
            continue
        for cont in sys_node.get("containers", []):
            if not cont.get("components"):
                warnings.append(f"Container '{cont['name']}' has no components — every @c2 needs at least one @c3")
    return warnings


SHORT_DESC_LIMIT = 80


def find_long_short_descriptions(workspace: dict, limit: int = SHORT_DESC_LIMIT) -> list[str]:
    """Return warnings for short_desc values over `limit` chars — short_desc is
    meant for the node card and sidebar header, not a second full description."""
    warnings: list[str] = []

    def _check(kind: str, name: str, short_desc: str) -> None:
        if short_desc and len(short_desc) > limit:
            warnings.append(
                f"{kind} '{name}' short_desc is {len(short_desc)} chars (limit {limit}) — trim it"
            )

    for sys_node in workspace["model"]["softwareSystems"]:
        _check("System", sys_node["name"], sys_node.get("short_desc", ""))
        for cont in sys_node.get("containers", []):
            _check("Container", cont["name"], cont.get("short_desc", ""))
            for comp in cont.get("components", []):
                _check("Component", comp["name"], comp.get("short_desc", ""))
    return warnings


EDGE_DESC_LIMIT = 100
EDGE_LABEL_LIMIT = 60
_BULLET_RE = re.compile(r"^\s*- \S")


def find_unreadable_descriptions(workspace: dict, edge_limit: int = EDGE_DESC_LIMIT) -> list[str]:
    """Return warnings for a description that is not a `- ` bullet list, a node with no short_desc, or an overlong edge label."""
    warnings: list[str] = []

    def _check_node(kind: str, node: dict) -> None:
        desc = node.get("description", "")
        lines = [line for line in desc.splitlines() if line.strip()]
        if lines and not all(_BULLET_RE.match(line) for line in lines):
            warnings.append(f"{kind} '{node['name']}' description is not a bullet list — write one `- ` line per thing it does")
        if desc and not node.get("short_desc"):
            warnings.append(f"{kind} '{node['name']}' has no short_desc — the node card needs a one-line summary")
        for rel in node.get("relationships", []):
            label = rel.get("description", "")
            if "; " in label:
                warnings.append(f"{kind} '{node['name']}' has an edge label joining flows with ';' — write one `- ` line per flow")
            if len(split_flows(label)) > 1 and not rel.get("short_desc"):
                warnings.append(f"{kind} '{node['name']}' has a multi-action edge with no short_desc — the canvas needs a one-line label")
            if len(rel.get("short_desc", "")) > EDGE_LABEL_LIMIT:
                warnings.append(f"{kind} '{node['name']}' has an edge short_desc over {EDGE_LABEL_LIMIT} chars — trim it")
            for flow in split_flows(label):
                if len(flow) > edge_limit:
                    warnings.append(
                        f"{kind} '{node['name']}' has a {len(flow)}-char edge flow (limit {edge_limit}) — say only what flows"
                    )

    for person in workspace["model"].get("people", []):
        _check_node("Person", person)
    for sys_node in workspace["model"]["softwareSystems"]:
        # System edges are rolled up from container edges, so only the description is checked here.
        _check_node("System", {**sys_node, "relationships": []})
        for cont in sys_node.get("containers", []):
            _check_node("Container", cont)
            for comp in cont.get("components", []):
                _check_node("Component", comp)
    return warnings


def build(elements: list[C4Element], line_counts: dict[str, int] | None = None) -> dict:
    # --- Phase 1: Collect elements ---
    # Systems keyed by name
    systems: dict[str, C4System] = {}
    # Containers keyed by name
    containers: dict[str, C4Container] = {}
    # Components keyed by (container_name, component_name) to allow same-named
    # components across different containers
    components: dict[tuple[str, str], C4Component] = {}
    # Lexicon entries keyed by term (last annotation for a given term wins)
    lexicon: dict[str, C4Lexicon] = {}
    # Human roles keyed by name, rendered at C1
    persons: dict[str, C4Person] = {}

    for el in elements:
        match el:
            case C4System():
                systems[el.name] = el
            case C4Person():
                persons[el.name] = el
            case C4Container():
                containers[el.name] = el
            case C4Component():
                components[(el.container, el.name)] = el
            case C4Lexicon():
                lexicon[el.term] = el

    # --- Phase 2: Validate hierarchy ---
    for c in containers.values():
        if c.system not in systems:
            raise C4ValidationError(
                f"container '{c.name}' references unknown system '{c.system}'",
                element_name=c.name,
            )
    for (cont_name, comp_name), comp in components.items():
        if comp.container not in containers:
            raise C4ValidationError(
                f"component '{comp.name}' references unknown container '{comp.container}'",
                element_name=comp.name,
            )

    for person in persons.values():
        for use in person.uses:
            target = _use_name(use)
            if target not in systems:
                raise C4ValidationError(
                    f"person '{person.name}' uses unknown system '{target}' — "
                    f"a person's uses: must name a system, since C1 shows systems",
                    element_name=person.name,
                )

    # --- Phase 2.5: Validate no duplicate uses targets ---
    # Two "uses: SameThing" entries mean two relationships to one node in the
    # diagram — the roles belong together in one description, not one edge each.
    for el in list(containers.values()) + list(components.values()):
        seen: dict[tuple[str, str], int] = {}
        for use in el.uses:
            key = (_use_name(use), _use_technology(use))
            seen[key] = seen.get(key, 0) + 1
        dupes = [name for (name, _technology), count in seen.items() if count > 1]
        if dupes:
            raise C4ValidationError(
                f"'{el.name}' uses '{dupes[0]}' more than once in uses: — "
                f"merge into a single entry describing both roles",
                element_name=el.name,
            )

    # --- Phase 3: Build element ID registry ---
    # system_ids: name -> id
    system_ids: dict[str, str] = {}
    for name in systems:
        system_ids[name] = _slug(name)

    # container_ids: name -> id
    container_ids: dict[str, str] = {}
    for name, cont in containers.items():
        container_ids[name] = f"{system_ids[cont.system]}-{_slug(name)}"

    # component_ids: (container_name, component_name) -> id
    component_ids: dict[tuple[str, str], str] = {}
    for (cont_name, comp_name), comp in components.items():
        component_ids[(cont_name, comp_name)] = f"{container_ids[cont_name]}-{_slug(comp_name)}"

    # --- Phase 4: Detect broker/external uses ---
    external_systems: dict[str, dict] = {}
    external_ids: dict[str, str] = {}
    for el in list(containers.values()) + list(components.values()):
        for use in el.uses:
            use_name = _use_name(use)
            if ":" in use_name and not use_name.startswith("http") and "/" not in use_name:
                ext_id = _slug(use_name)
                if use_name not in external_systems:
                    external_systems[use_name] = {
                        "id": ext_id,
                        "name": use_name,
                        "description": "",
                        "tags": "Element,Software System,External",
                        "relationships": [],
                        "containers": [],
                    }
                external_ids[use_name] = ext_id

    # --- Phase 5: Resolve uses references ---
    def _resolve_use(use: str, source_comp: C4Component) -> str:
        """
        Resolution order:
        1. ContainerName/ComponentName (qualified) -> exact component in that container
        2. protocol:name (broker/external) -> external system id
        3. Unqualified name -> local container first, then global (error if ambiguous/missing)
        """
        # Rule 1: qualified reference
        if "/" in use:
            parts = use.split("/", 1)
            cont_name, comp_name = parts[0].strip(), parts[1].strip()
            key = (cont_name, comp_name)
            if key not in component_ids:
                raise C4ValidationError(
                    f"'{source_comp.name}' uses qualified reference '{use}' "
                    f"but component '{comp_name}' not found in container '{cont_name}'",
                    element_name=source_comp.name,
                )
            return component_ids[key]

        # Rule 2: broker/external (contains colon, not http)
        if ":" in use and not use.startswith("http"):
            if use not in external_ids:
                raise C4ValidationError(
                    f"'{source_comp.name}' uses external '{use}' but it was not registered",
                    element_name=source_comp.name,
                )
            return external_ids[use]

        # Rule 3: unqualified name — local container first
        local_key = (source_comp.container, use)
        if local_key in component_ids:
            return component_ids[local_key]

        # Global lookup: check systems, containers, and components (all other containers)
        candidates: list[str] = []

        if use in system_ids:
            candidates.append(system_ids[use])
        if use in container_ids:
            candidates.append(container_ids[use])
        if use in external_ids:
            candidates.append(external_ids[use])
        # Check all components across all containers (excluding local, already checked)
        for (cont_name, comp_name), cid in component_ids.items():
            if comp_name == use and cont_name != source_comp.container:
                candidates.append(cid)

        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) == 0:
            raise C4ValidationError(
                f"'{source_comp.name}' uses unknown element '{use}'",
                element_name=source_comp.name,
            )
        else:
            raise C4ValidationError(
                f"'{source_comp.name}' uses ambiguous reference '{use}' "
                f"— matches {len(candidates)} elements; use ContainerName/ComponentName to qualify",
                element_name=source_comp.name,
            )

    def _build_component_relationships(comp: C4Component) -> list[dict]:
        rels = []
        source_id = component_ids[(comp.container, comp.name)]
        for use in comp.uses:
            use_name = _use_name(use)
            dest_id = _resolve_use(use_name, comp)
            rels.append({
                "id": f"rel-{source_id}-{dest_id}",
                "destinationId": dest_id,
                "description": _use_description(use),
                "short_desc": _use_short_desc(use),
                "technology": _use_technology(use),
                "tags": "Relationship",
            })
        return rels

    def _build_container_relationships(cont: C4Container) -> list[dict]:
        rels = []
        source_id = container_ids[cont.name]
        for use in cont.uses:
            use_name = _use_name(use)
            if use_name in system_ids:
                dest_id = system_ids[use_name]
            elif use_name in container_ids:
                dest_id = container_ids[use_name]
            elif use_name in external_ids:
                dest_id = external_ids[use_name]
            else:
                raise C4ValidationError(
                    f"container '{cont.name}' uses unknown element '{use_name}'",
                    element_name=cont.name,
                )
            rels.append({
                "id": f"rel-{source_id}-{dest_id}",
                "destinationId": dest_id,
                "description": _use_description(use),
                "short_desc": _use_short_desc(use),
                "technology": _use_technology(use),
                "tags": "Relationship",
            })
        return rels

    # --- Phase 5.5: Map every element id to its owning system id ---
    element_system: dict[str, str] = {}
    for name, sid in system_ids.items():
        element_system[sid] = sid
    for name, cid in container_ids.items():
        element_system[cid] = system_ids[containers[name].system]
    for (cont_name, _), comp_id in component_ids.items():
        element_system[comp_id] = system_ids[containers[cont_name].system]
    for ext_id in external_ids.values():
        element_system[ext_id] = ext_id

    def _rollup_system_relationships(sys_node: dict) -> list[dict]:
        """Derive system-level relationships from container/component uses that
        cross system boundaries (including external broker systems), carrying
        forward the underlying uses: description(s) so the C1 edge still says
        how the two systems interact instead of being left blank."""
        sys_id = sys_node["id"]
        merged: dict[str, list[dict]] = {}
        for cont in sys_node["containers"]:
            # A container's own edge already sums up its components', so theirs only count where it has none.
            own: dict[str, list[dict]] = {}
            inner: dict[str, list[dict]] = {}
            for rels, bucket in (
                (cont["relationships"], own),
                ([r for comp in cont["components"] for r in comp["relationships"]], inner),
            ):
                for rel in rels:
                    dest_sys = element_system.get(rel["destinationId"])
                    if dest_sys and dest_sys != sys_id:
                        merged.setdefault(dest_sys, [])
                        bucket.setdefault(dest_sys, []).append(rel)
            for dest_sys in {**own, **inner}:
                merged[dest_sys] += own[dest_sys] if dest_sys in own else inner[dest_sys]
        return [
            {
                "id": f"rel-{sys_id}-{dest_sys}",
                "destinationId": dest_sys,
                "description": merge_flows([r["description"].strip() for r in rels if r.get("description")]),
                "short_desc": merge_labels([edge_label(r) for r in rels]),
                "tags": "Relationship",
            }
            for dest_sys, rels in merged.items()
        ]

    # --- Phase 6: Assemble workspace ---
    cont_lines, comp_lines = attribute_lines(list(containers.values()), list(components.values()), line_counts or {})
    system_nodes = []
    container_views = []
    component_views = []

    for sys_name, sys in systems.items():
        sys_id = system_ids[sys_name]
        sys_containers = []

        for cont_name, cont in containers.items():
            if cont.system != sys_name:
                continue
            cont_id = container_ids[cont_name]
            comp_nodes = []

            for (c_cont, c_name), comp in components.items():
                if c_cont != cont_name:
                    continue
                comp_id = component_ids[(c_cont, c_name)]
                comp_nodes.append({
                    "id": comp_id,
                    "name": comp.name,
                    "description": comp.description,
                    "short_desc": comp.short_desc,
                    "technology": comp.technology,
                    "source_file": comp.source_file,
                    "tags": "Element,Component",
                    "relationships": _build_component_relationships(comp),
                })
                if line_counts is not None:
                    comp_nodes[-1]["loc"] = round(comp_lines.get((c_cont, c_name), 0))

            sys_containers.append({
                "id": cont_id,
                "name": cont.name,
                "description": cont.description,
                "short_desc": cont.short_desc,
                "technology": cont.technology,
                "source_file": cont.source_file,
                "tags": "Element,Container",
                "relationships": _build_container_relationships(cont),
                "components": comp_nodes,
            })
            if line_counts is not None:
                # A container weighs its own files plus all of its components'.
                inner = sum(comp_lines.get((cont_name, name), 0) for (c_cont, name) in components if c_cont == cont_name)
                sys_containers[-1]["loc"] = round(cont_lines.get(cont_name, 0) + inner)

            if comp_nodes:
                component_views.append({
                    "key": f"Components-{cont_id}",
                    "containerId": cont_id,
                })

        sys_node = {
            "id": sys_id,
            "name": sys.name,
            "description": sys.description,
            "short_desc": sys.short_desc,
            "tags": "Element,Software System" + (",External" if sys.external else ""),
            "relationships": [],
            "containers": sys_containers,
        }
        sys_node["relationships"] = _rollup_system_relationships(sys_node)
        if line_counts is not None:
            sys_node["loc"] = sum(c["loc"] for c in sys_containers)
        system_nodes.append(sys_node)

        if sys_containers:
            container_views.append({
                "key": f"Containers-{sys_id}",
                "softwareSystemId": sys_id,
            })

    all_systems = system_nodes + list(external_systems.values())
    # The primary/workspace-naming system should be the product under
    # documentation, not whichever @c1:system happened to be scanned first —
    # prefer the first non-external system, falling back to scan order only
    # when every declared system is external (unusual, but not invalid).
    non_external_names = [name for name, sys in systems.items() if not sys.external]
    primary_candidates = non_external_names or list(systems.keys())
    first_system_name = primary_candidates[0] if primary_candidates else None
    primary_system_id = system_ids[first_system_name] if first_system_name else ""

    people = []
    for name, person in persons.items():
        pid = f"person-{_slug(name)}"
        people.append({
            "id": pid,
            "name": name,
            "description": person.description,
            "short_desc": person.short_desc,
            "source_file": person.source_file,
            "tags": "Element,Person",
            "relationships": [
                {
                    "id": f"rel-{pid}-{system_ids[_use_name(use)]}",
                    "destinationId": system_ids[_use_name(use)],
                    "description": _use_description(use),
                    "short_desc": _use_short_desc(use),
                    "technology": _use_technology(use),
                    "tags": "Relationship",
                }
                for use in person.uses
            ],
        })

    return {
        "name": systems[first_system_name].name if first_system_name else "workspace",
        "lexicon": [
            {"term": entry.term, "definition": entry.definition}
            for entry in sorted(lexicon.values(), key=lambda e: e.term)
        ],
        "model": {
            "people": people,
            "softwareSystems": all_systems,
        },
        "views": {
            "systemContextViews": [
                {"key": "SystemContext", "softwareSystemId": primary_system_id}
            ] if primary_system_id else [],
            "containerViews": container_views,
            "componentViews": component_views,
            "configuration": {"styles": {"elements": [], "relationships": []}},
        },
    }
