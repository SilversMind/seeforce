# C4 Annotator Prompt

You are annotating a software codebase with C4 model markers so it can be visualized as a C4 architecture diagram.

## Step 0 — Detect Project Type

Before anything else, read `README.md`, `Cargo.toml`, `pyproject.toml`, `package.json`, `docker-compose.yml` (or equivalent) and classify the project as one of:

| Type | Signals |
|------|---------|
| **web** | Has a web server, REST/GraphQL API, or separate frontend; uses a DB; has deploy config (Dockerfile, k8s, Procfile) |
| **systems** | Single binary or library; no independently deployed services; subsystems are hardware emulation, compilers, CLI tools, desktop apps, embedded firmware, game engines, parsers |

**Announce your classification at the start** before writing any annotation:
> `Project type: web` or `Project type: systems`

If unsure, default to `systems`.

The type controls how C2 is interpreted — see below.

---

## C4 Model Rules

### Levels

**C1 — System Context**
- `system`: The software product being documented. One per deployable product or major bounded domain.
- `person`: A human *role* that interacts with the system (Admin, Customer, Player). Not an individual user — a role. **Always annotate person roles — missing persons are a common error.**
- `external`: An external system outside the boundary being documented (third-party API, SaaS, another team's service). Includes: email providers (SendGrid, Mailgun), payment processors (Stripe), auth providers (Auth0), cloud storage (S3), cache services (Redis) if hosted externally, etc.

**C2 — Containers**

Interpretation depends on project type:

**`web` projects** — a container is any independently deployable or runnable unit:
- Web application / API server
- Mobile application
- Desktop application
- Database / data store
- Message queue / event bus
- Serverless function
- File store / blob storage
- Background worker / job runner

Rule: if it runs as a separate process or is deployed independently → it is a C2 container.
Rule: a database is always C2, never C3.
Rule: infrastructure details like reverse proxies (nginx, Caddy) are deployment concerns — do not annotate them as C2 containers unless they perform business logic routing.

**`systems` projects** — a container is a major functional subsystem with a clear, bounded responsibility:
- A hardware emulation unit (CPU, PPU, APU, Memory Bus)
- A compiler pass or IR stage
- A game engine subsystem (renderer, physics, audio)
- A major CLI command group
- A distinct library module exposed as a public API

Rule: the entire binary is NOT a container — its subsystems are.
Rule: if a subsystem has fewer than 3 distinct internal concerns, it may be a C2 with no C3 children.
Rule: prefer 5–10 well-named containers over a flat single-container model.

**C3 — Components**
A component is a named grouping of related code *inside* one container with a clear, single responsibility.

Rule: do NOT annotate every class or function. Only annotate named architectural boundaries.
Rule: if the container is simple (< 3 logical concerns and no distinct sub-directories), skip C3 entirely.
Rule: prefer coarser boundaries — 5 well-named components beat 20 noisy ones.
Rule: for `systems` projects — after identifying a C2 container, scan its directory. If it contains 2+ distinct sub-modules or sub-directories with separate responsibilities, annotate them as C3. A C2 with an entire sub-directory structure and no C3 is almost always a missed opportunity.

**Relations**
- Describe *what happens*, not just "uses" (e.g. "sends payment events to", "authenticates via", "reads user records from")
- Relations follow runtime call/data flow, not static import graphs
- Only annotate relations that cross architectural boundaries
- When a container or component uses both REST and WebSocket, create separate `uses:` entries with `technology:` to distinguish them

### Common Judgment Calls

| Situation | Rule |
|-----------|------|
| `web`: Monorepo with multiple services | Each service with its own deploy = C2 container under one C1 system (if same domain) or separate C1 systems (if different products) |
| `web`: Django multiple `apps/` | Same process = C3 components inside one C2 container |
| `web`: Django separate worker process | Separate C2 container |
| `systems`: Single binary desktop app | Subsystems = C2 containers; no top-level "App" container |
| `systems`: Library with public modules | Public modules = C2 containers; internal helpers = C3 or skip |
| Third-party (Stripe, Auth0, S3, SendGrid, Mailgun) | C1 external system |
| Shared library / internal SDK | C3 component of whichever container uses it, or omit if infrastructure glue |
| When in doubt on C2 vs C3 | Default to C2 — coarser is better |
| When in doubt on C3 vs skip | Skip — noise is worse than missing detail |
| Missing person roles | Always add them — "Player", "Admin", "Customer" etc. |

---

## Annotation Format

Annotations live in the module-level or class-level docstring using a YAML block prefixed by `@c1`, `@c2`, or `@c3`.

Use the comment style appropriate for the language:
- Python: `""" ... """`
- Java, TypeScript, JS, Go, C#, Rust, C/C++: `/* ... */`

### C1 — System
```python
"""
@c1:system
name: Payment Platform
description: Handles all payment processing and subscription management for customers.
"""
```

### C1 — Person
```python
"""
@c1:person
name: Customer
description: End user who initiates purchases and manages their subscription.
"""
```

### C1 — External
```python
"""
@c1:external
name: Stripe
description: Third-party payment processor. Handles card charging and refunds.
"""
```

### C2 — Container
```python
"""
@c2:container
name: API Server
system: Payment Platform
technology: Python / Django + Daphne
description: Serves web and mobile clients via REST and WebSocket. Handles authentication and business logic.
uses:
- Database: "reads and writes application data"
- Redis Cache: "caches session tokens"
- Stripe: "initiates payment charges"
"""
```

### C3 — Component
```python
"""
@c3:component
name: Payment Service
container: API Server
technology: Django Ninja
description: Orchestrates payment intent creation, confirmation, and webhook handling.
uses:
- Subscription Manager: "updates subscription state after successful payment"
"""
```

**Technology field rules:**
- C2: use "Language / Framework" format, include all runtimes (e.g. "Python / Django + Daphne", "TypeScript / React + Vite")
- C3: omit the language if it is already stated in the C2 technology field. Only include the specific framework or library that adds meaningful context (e.g. "Django Ninja", "React Context", "Django Anymail"). If nothing specific, omit the field entirely.
- Never write "Python" alone in a C3 technology field if the parent C2 already says "Python / Django".

**Component naming rules:**
- Component name must not duplicate the container name. E.g., inside "API Server", do not create a component called "REST API" — use a more specific name like "Player HTTP API", "Auth API".
- Use business-domain names, not technical-layer names (not "Domain Layer" — use "Core Domain" or the actual domain name).

**Connectivity rules:**
- Every C3 component must have at least one edge (either via its own `uses:` or by being referenced in another component's `uses:`). Orphan components with no edges indicate a missing relationship — find and annotate it.
- External services mentioned in descriptions must appear as `@c1:external` annotations and be referenced in `uses:` fields, not buried in prose.

---

## Edge Technology Field

When you need to distinguish transport protocols between the same endpoints, add an optional `technology:` field to a uses entry:

```python
"""
@c2:container
name: Web App
system: Payment Platform
uses:
- API Server: "authenticates users and loads game data"
  technology: REST
- API Server: "receives live game events"
  technology: WebSocket
"""
```

This allows the visualization to show the protocol on each edge separately.

---

## Annotation Placement

- **Module-level**: place at the top of the file, before imports, as the module docstring
- **Class-level**: place inside the class body as the first docstring
- **Prefer module-level** for containers and components — it scopes the entire file

---

## Process

Follow these steps in order:

1. **Detect project type** — read manifest files (`Cargo.toml`, `package.json`, `pyproject.toml`, `docker-compose.yml`, `README.md`) and classify as `web` or `systems`. Announce the type.
2. **Identify the system** — name, purpose, tech stack, user roles (persons), external services
3. **Map C2 containers** — apply the type-specific C2 definition above; list them before writing any annotation
4. **Identify persons and externals** — annotate all person roles and external services at C1
5. **For each C2 container**: read its source directory and entry points — identify C3 component boundaries (skip if < 3 concerns)
6. **Infer relations** from imports, function calls, channel sends, HTTP clients, DB queries — runtime flow only
7. **Verify connectivity**: every C3 must have at least one edge; every external system must have at least one `uses:` pointing to it
8. **Write annotations** — one annotation per architectural element, no duplicates

---

## Output Requirements

- Output only the modified file contents, one file at a time
- Do not annotate files that have no architectural significance (migrations, tests, config boilerplate)
- Descriptions must state *responsibility* ("Processes incoming webhook events from Stripe"), not just restate the name ("Webhook handler")
- Keep descriptions to 1–2 sentences maximum
- Technology field in C3: omit if it would just repeat the parent C2 language
- All external services named in descriptions must have corresponding `@c1:external` annotations
- All person roles must have `@c1:person` annotations
