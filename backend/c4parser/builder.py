import re
from .types import C4System, C4Container, C4Component, C4Element
from .exceptions import C4ValidationError


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _use_name(entry: str | dict[str, str]) -> str:
    return next(iter(entry)) if isinstance(entry, dict) else entry


def _use_description(entry: str | dict[str, str]) -> str:
    if isinstance(entry, dict):
        return next(iter(entry.values()), "")
    return ""


def build(elements: list[C4Element]) -> dict:
    # --- Phase 1: Collect elements ---
    # Systems keyed by name
    systems: dict[str, C4System] = {}
    # Containers keyed by name
    containers: dict[str, C4Container] = {}
    # Components keyed by (container_name, component_name) to allow same-named
    # components across different containers
    components: dict[tuple[str, str], C4Component] = {}

    for el in elements:
        match el:
            case C4System():
                systems[el.name] = el
            case C4Container():
                containers[el.name] = el
            case C4Component():
                components[(el.container, el.name)] = el

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
        cross system boundaries (including external broker systems)."""
        sys_id = sys_node["id"]
        rels = []
        seen: set[str] = set()
        for cont in sys_node["containers"]:
            child_rels = cont["relationships"] + [
                r for comp in cont["components"] for r in comp["relationships"]
            ]
            for rel in child_rels:
                dest_sys = element_system.get(rel["destinationId"])
                if dest_sys and dest_sys != sys_id and dest_sys not in seen:
                    seen.add(dest_sys)
                    rels.append({
                        "id": f"rel-{sys_id}-{dest_sys}",
                        "destinationId": dest_sys,
                        "description": "",
                        "tags": "Relationship",
                    })
        return rels

    # --- Phase 6: Assemble workspace ---
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
                    "technology": comp.technology,
                    "tags": "Element,Component",
                    "relationships": _build_component_relationships(comp),
                })

            sys_containers.append({
                "id": cont_id,
                "name": cont.name,
                "description": cont.description,
                "technology": cont.technology,
                "tags": "Element,Container",
                "relationships": _build_container_relationships(cont),
                "components": comp_nodes,
            })

            if comp_nodes:
                component_views.append({
                    "key": f"Components-{cont_id}",
                    "containerId": cont_id,
                })

        sys_node = {
            "id": sys_id,
            "name": sys.name,
            "description": sys.description,
            "tags": "Element,Software System" + (",External" if sys.external else ""),
            "relationships": [],
            "containers": sys_containers,
        }
        sys_node["relationships"] = _rollup_system_relationships(sys_node)
        system_nodes.append(sys_node)

        if sys_containers:
            container_views.append({
                "key": f"Containers-{sys_id}",
                "softwareSystemId": sys_id,
            })

    all_systems = system_nodes + list(external_systems.values())
    first_system_name = next(iter(systems)) if systems else None
    primary_system_id = system_ids[first_system_name] if first_system_name else ""

    return {
        "name": systems[first_system_name].name if first_system_name else "workspace",
        "model": {
            "people": [],
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
