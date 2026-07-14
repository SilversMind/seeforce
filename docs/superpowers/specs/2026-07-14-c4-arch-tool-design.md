# C4 Architecture Tool — Design Spec
**Date:** 2026-07-14  
**Status:** Approved

---

## 1. Vision

Un outil SaaS de gestion de projet par l'architecture, inspiré du modèle C4. Pitch clé : **l'architecture vit dans le code et ne peut pas devenir stale**. Les annotations C4 sont co-localisées avec le code qu'elles décrivent — quand le code bouge, l'annotation bouge. Pas de manifest séparé à synchroniser.

---

## 2. Périmètre

### MVP (V1) — Local
- Parser Python qui scanne un repo local et génère `workspace.json`
- Viewer web (upload manuel du `workspace.json`)
- Graphe interactif React Flow, niveau C1 en entrée, drill-down C2/C3

### V1.1 — Validation officielle
- Sidecar Docker Structurizr Lite pour validation des règles C4

### V2 — SaaS
- GitHub OAuth, scan automatique, multi-tenant
- Structurizr Lite intégré dans le pipeline serveur

---

## 3. Stack technique

| Couche | Technologie |
|--------|-------------|
| Backend API | Python / Django + Django REST Framework |
| Parser | Python pur (`c4parser` package) |
| Format de sortie | `workspace.json` (format Structurizr) |
| Génération model | `structurizr-python` |
| Validation C4 | Structurizr Lite (Docker sidecar, V1.1) |
| Frontend | React + Vite |
| Graphe interactif | React Flow (`@xyflow/react`) |
| Data fetching | SWR |
| State navigation | Zustand |

---

## 4. Structure des repos

```
c4/
├── backend/
│   ├── c4_project/              # config Django
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   └── dev.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   └── graph/               # Django app : stocke + sert workspace.json
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       ├── transformers.py  # workspace.json → React Flow nodes/edges
│   │       ├── urls.py
│   │       └── management/
│   │           └── commands/
│   │               └── scan.py  # thin wrapper → appelle c4parser.scan()
│   ├── c4parser/                # package Python standalone, pip-installable
│   │   ├── __init__.py          # API publique
│   │   ├── scanner.py           # AST walker + extraction annotations YAML
│   │   ├── builder.py           # construit modèle structurizr-python
│   │   ├── exporter.py          # sérialise → workspace.json
│   │   ├── exceptions.py        # C4ParseError, C4ValidationError
│   │   └── types.py             # dataclasses internes
│   ├── tests/
│   │   └── c4parser/
│   │       ├── test_scanner.py
│   │       └── test_builder.py
│   ├── pyproject.toml
│   └── manage.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Graph/
│   │   │       ├── C4Graph.tsx
│   │   │       ├── nodes/
│   │   │       │   ├── SystemNode.tsx
│   │   │       │   ├── ContainerNode.tsx
│   │   │       │   ├── ComponentNode.tsx
│   │   │       │   ├── PersonNode.tsx
│   │   │       │   └── ExternalNode.tsx
│   │   │       └── edges/
│   │   │           └── RelationEdge.tsx
│   │   ├── hooks/
│   │   │   └── useWorkspace.ts
│   │   ├── pages/
│   │   │   └── GraphView.tsx
│   │   └── services/
│   │       └── api.ts
│   ├── vite.config.ts
│   └── package.json
│
├── docker/
│   └── structurizr-lite/        # sidecar validation (V1.1)
│
└── docker-compose.yml
```

---

## 5. Format d'annotation — YAML bloc dans commentaires

Annotations co-localisées dans le code source. Parsées statiquement (AST) — aucun import, aucune exécution du code cible.

### Syntaxe

Préfixe numérique `@c1:` / `@c2:` / `@c3:` — le niveau de zoom est immédiatement lisible. `grep -r "@c2:"` liste tous les containers d'un repo.

```python
# racine projet — apps/c4_project/__init__.py
"""
@c1:system
name: E-commerce Platform
description: Handles all e-commerce operations
"""

# apps/orders/apps.py (Django AppConfig = natural C2 placement)
class OrdersConfig(AppConfig):
    """
    @c2:container
    name: Orders Service
    system: E-commerce Platform
    technology: Python/Django
    description: Handles order lifecycle
    """
    name = 'orders'

# apps/orders/services.py
class OrderProcessor:
    """
    @c3:component
    name: Order Processor
    container: Orders Service
    technology: Django
    uses:
      - Payment Service
      - kafka:order-events
    """
```

Même format en Java, Go, TypeScript — le scanner cherche `@c[123]:` dans tout fichier texte, sans convention de placement imposée.

### Champs par niveau

| Champ | C1 `@c1:system` | C2 `@c2:container` | C3 `@c3:component` |
|-------|-----------|--------------|--------------|
| `name` | requis | requis | requis |
| `description` | optionnel | optionnel | optionnel |
| `system` | — | requis | — |
| `container` | — | — | requis |
| `technology` | — | optionnel | optionnel |
| `uses` | — | optionnel | optionnel |
| `external` | optionnel | — | — |

### Convention `uses` — résolution et nommage

```yaml
uses:
  - Payment Service              # même container → résolution locale en premier
  - Inventory API/Stock Check    # cross-container → nom qualifié Container/Component
  - kafka:order-events           # broker async → préfixe protocol:nom
  - redis:session-cache          # idem
```

**Ordre de résolution dans le builder :**
1. Si `/` présent → lookup qualifié `Container/Component` exact
2. Sinon → lookup local dans le même container d'abord
3. Sinon → lookup global sur tous les éléments
4. Ambigu ou introuvable → `C4ValidationError` avec message explicite

### Language agnosticism

Format identique en Java, Go, TypeScript — parser cherche `@c4:` dans tout fichier texte :

```java
/**
 * @c4:component
 * name: Order Service
 * container: API Backend
 * technology: Java/Spring
 * uses:
 *   - Payment Service
 */
public class OrderService { ... }
```

---

## 6. Pipeline de génération

```
repo cible (fichiers source annotés)
        │
        ▼
c4parser.scanner.scan(root_path)
  → walk fichiers source (*.py, *.java, *.ts, *.go…)
  → regex détecte blocs @c4:
  → PyYAML parse chaque bloc
  → retourne List[C4System | C4Container | C4Component]
        │
        ▼
c4parser.builder.build(elements)
  → construit modèle structurizr-python en mémoire
  → résout relations uses[] (lookup par name)
  → relations brokers → external systems
        │
        ▼
c4parser.exporter.export_workspace(model) → workspace.json
        │
        ▼
[V1]  `python manage.py scan /path/to/repo` → génère workspace.json local
        → deux options : upload manuel via UI OU `--upload` flag qui POST directement à /api/graph/upload/
[V1.1] POST → Structurizr Lite (validation règles C4) → workspace.json validé
[V2]  pipeline serveur, déclenché par webhook GitHub
```

---

## 7. Règles C4 (enforced par Structurizr Lite en V1.1)

```
C3 appartient à exactement un C2
C2 appartient à exactement un C1
C3 → C3 : uniquement au sein du même container
C3 → C2 : uniquement vers containers externes (pas son propre parent)
C2 → C2 : libre entre containers
C2 → C1 : uniquement vers systèmes externes (external: true)
Noms uniques au sein du même scope
```

En V1 (sans Structurizr Lite) : `structurizr-python` assure une validation partielle. Hard error sur violations détectées.

---

## 8. Django API — `graph` app

### Endpoints MVP

```
POST /api/graph/upload/              # reçoit workspace.json
GET  /api/graph/{id}/                # retourne workspace.json brut
GET  /api/graph/{id}/view/C1/        # nodes/edges React Flow niveau C1
GET  /api/graph/{id}/view/C2/?system=X    # drill-down container
GET  /api/graph/{id}/view/C3/?container=Y # drill-down component
```

### Model

```python
class Workspace(models.Model):
    name        = models.CharField(max_length=255)
    source_json = models.JSONField()
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
```

La transformation `workspace.json → {nodes, edges}` React Flow vit dans `transformers.py` — logique pure, testable sans HTTP.

---

## 9. Frontend — React Flow

### Navigation drill-down

```
ViewState { level: "C1" }
  → double-click système → ViewState { level: "C2", systemId: "X" }
      → double-click container → ViewState { level: "C3", containerId: "Y" }
          → breadcrumb pour remonter
```

### Node types

| Type | Niveau | Visuel |
|------|--------|--------|
| `SystemNode` | C1 | Rectangle large |
| `ContainerNode` | C2 | Rectangle + badge technologie |
| `ComponentNode` | C3 | Rectangle compact |
| `PersonNode` | C1 | Silhouette personne |
| `ExternalNode` | C1/C2 | Rectangle pointillé |

### Hook principal

```ts
const useWorkspace = (id: string, view: ViewState) => {
  const { data } = useSWR(`/api/graph/${id}/view/${view.level}/`, fetcher)
  return { nodes: data?.nodes ?? [], edges: data?.edges ?? [] }
}
```

Le frontend est stateless vis-à-vis de la transformation — il reçoit `{nodes, edges}` prêts à passer à React Flow. Toute la logique métier est côté Django.

---

## 10. C4 de l'outil lui-même

L'outil se décrit via son propre format :

```
C1 : C4 Tool
  C2 : API Backend (Django)
    C3 : c4parser         uses → Structurizr Lite
    C3 : graph app        uses → PostgreSQL
  C2 : Frontend (React)
    C3 : C4Graph          uses → API Backend
  C2 : Structurizr Lite  [external sidecar]
  C2 : PostgreSQL         [external]
```

---

## 11. Performance du scanner

Bottleneck = I/O disque, pas CPU. Python suffisant — pas besoin de Rust.

**Flow optimisé :**
1. `os.walk` → liste fichiers
2. Filtre extensions (`.py`, `.java`, `.ts`, `.go`, etc.)
3. Exclusions par défaut : `node_modules/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `vendor/`
4. `.c4ignore` à la racine pour exclusions custom (même syntaxe `.gitignore`)
5. Regex rapide `@c[123]:` — si pas de match → next (coût quasi nul)
6. Si match → extraction + parse YAML (rare, ~0.1% des fichiers)
7. Cache : hash SHA du fichier → skip si inchangé depuis dernier scan

**Estimations sans cache :**

| Taille repo | Fichiers source | Temps estimé |
|-------------|-----------------|--------------|
| Petit | 1k–10k | < 1s |
| Moyen | 10k–100k | 1–5s |
| Grand monorepo | 100k–1M | 10–60s |

Avec cache : rescan quasi instantané (seuls les fichiers modifiés relus).

---

## 12. Refresh du graphe frontend

```
V1   : bouton "Refresh" → re-fetch /api/graph/{id}/ (scan relancé manuellement avant)
V1.1 : manage.py scan --upload → POST nouveau workspace → SSE notif → frontend auto-refresh
V2   : GitHub webhook → scan auto → WebSocket push vers clients connectés
```

---

## 13. Décisions différées (hors scope V1)

- Enrichissement manuel des composants (descriptions, liens custom) — V2
- Scaffolding inversé (créer fichiers depuis l'archi) — V2+
- GitHub OAuth + scan automatique — V2
- Support multi-tenant — V2
- Plugins IDE pour validation inline des annotations — V2+
- Graph database (Neo4j, ArangoDB) — V3+ uniquement si features d'impact analysis transitif ou cross-workspace queries; PostgreSQL JSONB suffisant jusqu'alors
