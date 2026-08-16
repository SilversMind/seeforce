# Lexique per-projet — Design Spec

## Context

Quand on navigue des diagrammes C4 de projets techniques (émulateurs, compilateurs, firmware), les descriptions des nœuds contiennent des acronymes opaques (SM83, DMA, MBC, PPU) difficiles à comprendre pour un lecteur non familier du domaine. Un lexique per-projet permet au mainteneur de définir des termes une seule fois ; ces termes apparaissent ensuite en bleu dans toutes les descriptions de nœuds et révèlent leur définition au clic via un panneau bas.

## Data Model

### LexiconEntry (nouveau modèle Django)

```python
class LexiconEntry(models.Model):
    project_map = models.ForeignKey(ProjectMap, on_delete=models.CASCADE, related_name="lexicon_entries")
    term        = models.CharField(max_length=255)         # stored as-entered, matched case-insensitively
    definition  = models.TextField()
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("project_map", "term")]
```

Migration: `0004_lexicon_entry.py`

## API

Tous les endpoints sous `/api/graph/<project_map_id>/` :

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `lexicon/` | — | `[{term, definition}]` |
| POST | `lexicon/` | `{term, definition}` | `{ok: true}` |
| DELETE | `lexicon/<str:term>/` | — | 204 No Content |

Pattern : même `get_or_create` que `upsert_node_overlay`. Serializer plain `serializers.Serializer`.

## Frontend Architecture

### Utility: `highlightTerms`

Fichier : `frontend/src/lib/lexicon.ts`

```ts
export interface LexiconEntry { term: string; definition: string }
export type Segment =
  | { type: 'text'; content: string }
  | { type: 'term'; content: string; entry: LexiconEntry }

export function highlightTerms(text: string, lexicon: LexiconEntry[]): Segment[]
```

- Matching case-insensitive (regex `new RegExp(term, 'gi')`)
- En cas de termes qui se chevauchent : préférence au terme le plus long
- Retourne les segments dans l'ordre d'apparition dans le texte

### LexiconContext

Dans `C4Graph.tsx` : contexte React qui fournit `{lexicon, activeTerm, setActiveTerm}` à tous les composants de nœud. Lexique chargé via SWR (`fetchLexicon(projectMapId)`). Évite de polluer le `data` prop ReactFlow.

### Rendu des descriptions

Composant partagé `DescriptionWithHighlights` (inline dans `C4Graph.tsx`) :
- Consomme `LexiconContext`
- Appelle `highlightTerms`
- Rend les segments `term` comme `<span style={{color: "var(--c4-system-border)", cursor: "pointer", textDecoration: "underline"}}>`
- `onClick` → `setActiveTerm(entry)`

Chaque composant nœud (`SystemNode`, `ContainerNode`, `ComponentNode`, `PersonNode`, `ExternalNode`) remplace son rendu de description statique par `<DescriptionWithHighlights text={data.description} />`.

### LexiconBottomPanel

Fichier : `frontend/src/components/Graph/LexiconBottomPanel.tsx`

- `position: fixed`, `bottom: 0`, `left: 0`, `right: 0`
- Hauteur : `clamp(100px, 18vh, 180px)`
- Animation slide-up : `transform: translateY(0 ou 100%)`, `transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1)`
- Affiche : label terme (header), définition (corps)
- Fermeture : bouton ×, ou touche Escape
- Se ferme aussi si `activeTerm` passe à null (click pane, drill-down, etc.)

### Section Lexique dans OverlaySidebar

Nouvelle section en bas de `OverlaySidebar.tsx`, visible uniquement quand un nœud est sélectionné :
- Header : "LEXIQUE" (même style uppercase/muted que autres sections)
- Formulaire : champ `term` (input) + `definition` (textarea) + bouton Save
- Save → `upsertLexiconEntry` + `mutate` SWR key → terme actif dans toutes les descriptions
- Liste les termes déjà définis qui apparaissent dans la description du nœud sélectionné (read-only avec bouton ×  delete)

### Modifications api.ts

```ts
export interface LexiconEntry { term: string; definition: string }
export async function fetchLexicon(projectMapId: number): Promise<LexiconEntry[]>
export async function upsertLexiconEntry(projectMapId: number, term: string, definition: string): Promise<void>
export async function deleteLexiconEntry(projectMapId: number, term: string): Promise<void>
```

## Hors scope v1

- Sources / URLs
- Matching dans les labels de nœuds (noms)
- Matching dans les labels d'arêtes
- Import/export du lexique
- Suggestions automatiques de termes

## Vérification

1. `uv run pytest` — tests backend passent
2. Scanner xenogb, ouvrir le projet
3. Sélectionner nœud CPU → section Lexique dans OverlaySidebar → ajouter "SM83" + définition → Save
4. "SM83" apparaît en bleu dans la description du nœud CPU + tout autre nœud contenant "SM83" dans sa description
5. Cliquer "SM83" bleu → panneau bas slide-up avec la définition
6. Escape → panneau se ferme
7. Tester case-insensitivity : description avec "sm83" en minuscules → doit aussi matcher
8. Supprimer l'entrée depuis OverlaySidebar → terme redevient texte normal
