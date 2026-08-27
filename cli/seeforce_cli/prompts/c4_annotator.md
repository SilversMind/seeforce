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

## Description Skeleton

Every description is built from up to three slots. Write them as flowing prose — fold slots into one sentence when they fit naturally — not as a rigid template with visible labels.

**1. Responsibility (required, every level).** One verb-first clause naming the single thing this element is for. No lists, no "and" stacking multiple unrelated jobs — if stating the job needs a list, that's usually a sign the element should be split into separate C2/C3 elements instead.

**2. Context (required at C1/C2; skip at C3 unless the name+container leave real ambiguity).** Why this exists relative to its parent — not what *category* of thing it is (that's the `technology:` field's job), and not a restatement of a fact the graph already shows. Don't write "shared by X and Y" when the diagram already draws incoming edges from both X and Y — the structure says that, the prose doesn't need to repeat it. At C1 specifically, context takes a fixed, separate form: a standalone closing sentence, `Used to answer "..."`, phrased as the question a stakeholder would actually ask (see the C1 rule below) — never fold this one into the responsibility sentence.

**3. Boundary (optional, every level — use sparingly).** Only include it when its absence would let a reader assume something false — a real misattribution risk, not padding. Can be a full trailing sentence, or a short parenthetical when brief (`(never re-parses source files itself)`).

**Never include mechanism, at any level.** *How* something works internally — algorithms, call sequences, specific functions — belongs in the code, not in any annotation. This applies even to the responsibility sentence: "parses annotations embedded in a repo's source files" describes an *approach*; "shows an interactive map of your architecture" describes the *outcome*. Prefer the outcome framing; if a reader wants the *how*, that's what the source-file link is for.

**Entity lists are fine; feature/operation lists are not.** Naming what something *persists* or *owns* — "projects, overlays, lexicon entries, share links" — is one coherent concern and stays fine as a list. Naming the *operations* it performs — "handles CRUD, overlays, lexicon, sharing, and sync" — is the anti-pattern: it's a list of distinct responsibilities in disguise. Each one with real architectural weight should either be its own C3 component, or is already covered by that component's own description one level down — don't pre-summarize it here.

**Length stays 1–2 sentences**, plus the mandatory `Used to answer "..."` sentence at C1 and the optional boundary clause. If it doesn't fit, the description is trying to say too much — cut, don't run on.

Before finalizing any description, check it against this list: does it name a mechanism instead of an outcome? Does it restate the `technology:` field or an obvious category fact? Does it restate something already visible from the element's own edges? Does it enumerate operations instead of entities? Rewrite anything that does.

### C1 — System
```python
"""
@c1:system
name: Payment Platform
description: Handles all payment processing and subscription management for customers. Used to answer "can this customer be charged, and are they current on their subscription?"
"""
```
Rule: end the C1 system description with the single plain-language question this system exists to answer (in quotes, phrased the way a stakeholder would actually ask it — "does any machine show a match for this compromised package/version?", "can this customer be charged?"). This is the single most important sentence in the whole annotation set — it's what makes the diagram legible to someone who has never seen the codebase. Never skip it.

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
description: Third-party payment processor, hosted by Stripe (not part of this codebase). Handles card charging and refunds; the platform calls it via the Stripe REST API to create charges and process webhook confirmations.
"""
```
Rule: an external's description must answer two things a newcomer can't infer from the name alone — **where it lives** (whose infrastructure, not part of this repo) and **what role it plays** (what this system actually does with it, not just "third-party service"). "Third-party payment processor" alone is not enough — see the example above.

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
- Every C2 container and every C3 component must have at least one edge in either direction (its own `uses:`, or being named in another element's `uses:`). A container or component nothing calls and that calls nothing isn't doing anything at that level — it either needs a relationship you missed, or it doesn't belong as its own C2/C3 element (fold it into whatever it's actually part of).
- Orphan elements with no edges indicate a missing relationship — find and annotate it. `seeforce scan` will warn about any orphans it finds; treat those warnings as required fixes, not noise.
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
6. **Infer relations** from imports, function calls, channel sends, HTTP clients, DB queries — runtime flow only
7. **Verify connectivity**: every C2 and C3 must have at least one edge in either direction; every external system must have at least one `uses:` pointing to it
8. **Scan every description you're about to write for jargon** — domain terms, acronyms, internal conventions, protocol/format names a newcomer wouldn't know — and add a `@lexicon` entry for each
9. **Check every description against the Description Skeleton** (see above) — mechanism instead of outcome, restated `technology:`/graph-visible facts, operation-lists instead of entity-lists, missing or superfluous context/boundary. Rewrite anything that fails before moving on.
10. **Write annotations** — one annotation per architectural element, no duplicates

---

## Output Requirements

- Output only the modified file contents, one file at a time
- Do not annotate files that have no architectural significance (migrations, tests, config boilerplate)
- Descriptions must follow the Description Skeleton — responsibility as outcome not mechanism, not just a restated name ("Webhook handler" → "Processes incoming webhook events from Stripe")
- Keep descriptions to 1–2 sentences maximum, except the `@c1:system` description, which gets one extra sentence for its closing "used to answer ..." question — never omit that question
- Technology field in C3: omit if it would just repeat the parent C2 language
- All external services named in descriptions must have corresponding `@c1:external` annotations
- All person roles must have `@c1:person` annotations
- Any domain-specific or repo-specific jargon in a description must have a corresponding `@lexicon` entry — see the Lexicon section above
