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
Rule: before splitting a container into multiple C3 components, check that each proposed component will actually have its own edge — either its own `uses:`, or being named in another element's `uses:`. Two functions being logically distinct in the code isn't enough to justify a split if nothing at that granularity calls into one of them; if you can't find a real caller or callee for a candidate component, fold it back into the container's own description instead of giving it a component that will show up as a disconnected orphan.

**Relations**
- Describe *what happens*, not just "uses" (e.g. "sends payment events to", "authenticates via", "reads user records from")
- If the call passes or returns a specific domain object (a struct/record type central to the codebase, e.g. a `Finding`, an `Order`, a `Record`), name it in the description and say what happens to it (returned to the caller, forwarded to X, persisted) — don't describe only the trigger side of the call and leave the reader to guess what comes back or where it goes next
- Relations follow runtime call/data flow, not static import graphs
- Only annotate relations that cross architectural boundaries
- When a container or component uses both REST and WebSocket, create separate `uses:` entries with `technology:` to distinguish them
- **Never create a reverse edge between a pair that's already connected.** Before adding `A uses: B`, check whether `B` (or one of `B`'s existing edges) already points back at `A`. If the relationship already exists in one direction, don't add the opposite direction too — pick the dominant call direction and describe it once. Two edges between the same pair, one each way, render as a single bidirectional arrow and lose meaning.
- **Never mix levels in a `uses:` list.** A `@c2:container`'s `uses:` may only name other `@c1` systems/externals or other `@c2` containers — never a `@c3:component`, even one that lives inside a container it already uses. If the real call target is a component inside another container, either point the `uses:` at that container instead, or add a `@c3:component` annotation to the actual calling code inside *this* container and put the component-level `uses:` there (component→component references are allowed and must be qualified with `ContainerName/ComponentName` if the name is ambiguous across containers).

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

Every field value is parsed as YAML — never start a `description:`/`term:`/`definition:` value with a `"` character (e.g. `description: "python manage.py scan" — does X`). YAML treats a leading quote as the start of a flow scalar and fails to parse anything after the matching closing quote on the same line. Quoting a command or literal mid-sentence is fine; starting the value with one is not.

## Descriptions

Every element carries two texts, read in two places: `short_desc` on the node card, `description` in the sidebar when the node is opened. Both are read by someone scanning the diagram, so they must cost as little reading as possible.

**`short_desc` (required, every level).** One line, verb-first, 80 characters at most — the single job of the element, phrased as an outcome ("Serves the REST API and stores every project", not "Django app with views and serializers").

**`description` (required, every level).** A bullet list of what the element does, one `- ` line per responsibility, written as a YAML literal block so it reads in the source exactly as it renders:

```yaml
description: |
  - Serves the REST API for:
    - Project CRUD
    - Node/edge overlays
    - GitHub import, sync and link
  - Persists projects in the Database
```

Rules for the list:
- **One responsibility per bullet**, verb-first, a few words. A bullet that needs "and" to say two things is two bullets.
- **Nest only to group**: a parent bullet ending with `:` introduces the sub-items it covers (endpoints, entities, commands). Two levels at most.
- **Only what the element does.** Never write what it does not do ("does not parse files itself"), and never restate a relation an edge already draws ("delegates parsing to X", "called by Y") — the edge says it, the reader sees it.
- **No mechanism**: algorithms, call sequences, function names belong in the code; the source-file link is there for the *how*.
- **No restated metadata**: the `technology:` field and the element's name already say what kind of thing it is.
- **3–6 top-level bullets.** More means the element is doing too much and should probably be split into C3 components.
- **Each leaf bullet is a capability.** A parent that only groups is not one; its children are. The comparison view diffs capabilities one by one (added, removed, reworded), so when the code changes, edit the one bullet it touches and leave the others word for word.

A YAML list (`description:` followed by `- item` lines, nested via `item:` keys) is accepted too and renders the same, but the literal block (`|`) is safer: a bullet starting with a quote or containing `: ` cannot break the YAML.

`seeforce scan` warns on any description that is not a bullet list, on any element with no `short_desc`, and on any edge flow over 100 characters or joined with ";", and on any multi-action edge with no `short_desc` (or one over 60 characters) — treat those warnings as required fixes.

### Edge descriptions

The text of a `uses:` entry is the edge label on the canvas. It says **what flows**, one flow per phrase:
- Verb-first, naming the domain object and what happens to it ("persists projects", "fetches workspace.json at a commit").
- **One action per phrase.** When the edge carries several ("authenticates the user and fetches the project id"), write them as a YAML list, one item per action — never joined with "and", ";" or ",".
- **A multi-action edge also gets a `short_desc`**: the label drawn on the graph, 60 characters at most, verb-first, naming the main actions tersely. The graph shows it with a badge counting the actions; the full list stays in the sidebar.

```yaml
uses:
- Backend:
  - "authenticates the user"
  - "fetches the project id the MCP server registers against"
  short_desc: "authenticates, fetches project id"
  technology: REST
```

A single-action edge needs no `short_desc`: its one phrase is the label.

- 100 characters at most per item.
- Never explain *why* or *how* (no endpoint paths, token lifetimes, library names) — that belongs in the source.
- A container's edge sums up what its components send along the same path; the C1 edge is built from it, so keep it complete.

### C1 — System
```python
"""
@c1:system
name: Payment Platform
short_desc: Charges customers and keeps their subscriptions current
description: |
  - Charges customers for one-off purchases
  - Manages subscriptions and renewals
  - Answers "can this customer be charged, and are they current on their subscription?"
"""
```
Rule: end the C1 system description with an `Answers "..."` bullet: the single plain-language question this system exists to answer, phrased the way a stakeholder would actually ask it ("does any machine show a match for this compromised package/version?", "can this customer be charged?"). This is the single most important line in the whole annotation set — it's what makes the diagram legible to someone who has never seen the codebase. Never skip it.

### C1 — Person
```python
"""
@c1:person
name: Customer
short_desc: Buys products and manages their subscription
description: |
  - Initiates purchases
  - Manages their subscription
"""
```

### C1 — External
```python
"""
@c1:external
name: Stripe
short_desc: Third-party payment processor hosted by Stripe
description: |
  - Charges cards and issues refunds for the platform
  - Confirms each charge back through webhooks
"""
```
Rule: an external must tell a newcomer two things they can't infer from the name alone — **where it lives** (whose infrastructure, not part of this repo; usually in `short_desc`) and **what role it plays** for this system (the bullets). "Third-party payment processor" alone is not enough — see the example above.

### C2 — Container
```python
"""
@c2:container
name: API Server
system: Payment Platform
technology: Python / Django + Daphne
short_desc: Serves the web and mobile clients
description: |
  - Authenticates users
  - Serves the REST API for:
    - Orders
    - Subscriptions
  - Pushes live order updates over WebSocket
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
short_desc: Runs a payment from intent to confirmation
description: |
  - Creates payment intents
  - Confirms payments from Stripe webhooks
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
- Every C2 container and every C3 component must have at least one edge in either direction (its own `uses:`, or being named in another element's `uses:`). A container or component nothing calls and that calls nothing isn't doing anything at that level — it either needs a relationship you missed, or it doesn't belong as its own C2/C3 element (fold it into whatever it's actually part of).
- Orphan elements with no edges indicate a missing relationship — find and annotate it. `seeforce scan` will warn about any orphans it finds; treat those warnings as required fixes, not noise.
- External services an element talks to must appear as `@c1:external` annotations and be referenced in `uses:` fields, not named in description bullets.

---

## Edge Technology Field

When you need to distinguish transport protocols between the same endpoints, add an optional `technology:` field to a uses entry:

```python
"""
@c2:container
name: Web App
system: Payment Platform
uses:
- API Server: "loads game data for the signed-in user"
  technology: REST
- API Server: "receives live game events"
  technology: WebSocket
"""
```

This allows the visualization to show the protocol on each edge separately.

---

## Lexicon

Treat the viewer as someone **totally unfamiliar with this repo and its problem domain** — not a teammate, not someone who already knows the jargon. Any word in a description that names a domain concept, internal convention, protocol, file format, or acronym specific to this codebase or its industry needs a lexicon entry, even if it feels obvious to someone who just read the source.

Examples of terms that need an entry: "ecosystem detector", "per-scan time bound", "OSV schema", "webhook confirmation", "wildcard entry", "bounded context" — anything a reader can't resolve from general programming knowledge alone.

Add one `@lexicon` block per term, anywhere in the codebase (module-level docstring is fine, doesn't need to live near the term's first use):

```python
"""
@lexicon
term: ecosystem detector
definition: A per-package-manager parser (npm, PyPI, RubyGems, etc.) that recognizes and extracts records from that ecosystem's manifest or lock files.
"""
```

Rule: definitions must stand alone — don't define a term using another undefined term.
Rule: don't create an entry for words that are standard software engineering vocabulary (e.g. "component", "endpoint", "cache") — only domain- or repo-specific jargon.
Rule: one entry per term, case-insensitive dedup (don't add both "OSV" and "osv").

---

## Annotation Placement

- **Module-level**: place at the top of the file, before imports, as the module docstring
- **Class-level**: place inside the class body as the first docstring
- **Prefer module-level** for containers and components — it scopes the entire file

---

## Process

Follow these steps in order:

1. **Detect project type** — read manifest files (`Cargo.toml`, `package.json`, `pyproject.toml`, `docker-compose.yml`, `README.md`) and classify as `web` or `systems`. Announce the type.
2. **Identify the system** — name, purpose, tech stack, user roles (persons), external services, and the one plain-language question this system exists to answer
3. **Map C2 containers** — apply the type-specific C2 definition above; list them before writing any annotation
4. **Identify persons and externals** — annotate all person roles and external services at C1
5. **For each C2 container**: read its source directory and entry points — identify C3 component boundaries (skip if < 3 concerns)
6. **Infer relations** from imports, function calls, channel sends, HTTP clients, DB queries — runtime flow only. If the `get_static_facts_for_files` MCP tool is available, cross-check its candidate edges for the files you're annotating before finalizing relations: it catches imports you might otherwise miss (a recall aid), but it is NOT verified truth. Confirm each candidate reflects real runtime usage — not just an unused import — before annotating it. It also cannot see dynamic wiring (DI containers, plugin registries, reflection, config-driven routes, message-bus subscriptions); keep searching for those independently. A missing static candidate is not evidence that a relation doesn't exist.
7. **Verify connectivity**: every C2 and C3 must have at least one edge in either direction; every external system must have at least one `uses:` pointing to it
8. **Scan every description you're about to write for jargon** — domain terms, acronyms, internal conventions, protocol/format names a newcomer wouldn't know — and add a `@lexicon` entry for each
9. **Check every text against the Descriptions rules** (see above) — `short_desc` on one line, `description` as a bullet list of what the element does, nothing it doesn't do, no relation an edge already draws, no mechanism, edge labels with one action per item, under 100 characters each, and a `short_desc` on every multi-action edge. Rewrite anything that fails before moving on.
10. **Write annotations** — one annotation per architectural element, no duplicates

---

## Output Requirements

- Output only the modified file contents, one file at a time
- Do not annotate files that have no architectural significance (migrations, tests, config boilerplate)
- Every element has a one-line `short_desc` and a bullet-list `description` following the Descriptions rules — outcomes, not mechanism, not just a restated name ("Webhook handler" → "- Processes incoming webhook events from Stripe")
- The `@c1:system` description ends with its `Answers "..."` bullet — never omit that question
- Technology field in C3: omit if it would just repeat the parent C2 language
- All external services named in descriptions must have corresponding `@c1:external` annotations
- All person roles must have `@c1:person` annotations
- Any domain-specific or repo-specific jargon in a description must have a corresponding `@lexicon` entry — see the Lexicon section above
