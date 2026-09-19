# C4 Project — Claude Rules

## Before any important change

Before implementing any significant feature, new service, new module, or architectural shift — ask:

> "Est-ce que ce changement mérite d'être documenté dans la codebase C4 (nouveau Container, Component, ou relation) pour que l'architecture reste à jour ?"

Si oui, proposer les éléments C4 à ajouter/modifier avant de coder.

### Ce qui compte comme "important"
- Nouveau service ou app (Container C4)
- Nouveau module fonctionnel distinct (Component C4)
- Nouvelle dépendance externe (base de données, API tierce, auth provider)
- Changement de protocole de communication entre composants
- Ajout d'un boundary (bounded context, zone réseau, domaine)

### Ce qui ne nécessite pas de mise à jour C4
- Bugfixes
- Refactoring interne à un composant
- Changements UI cosmétiques
- Ajout de champs sur modèle existant

## Après un changement — vérifier la dérive (drift)

Un Stop hook (`.claude/hooks/arch-sync-check.sh`) tourne automatiquement à la fin de chaque tour. Il regarde uniquement les fichiers source non commités et cherche des signaux structurels bon marché (nouveau fichier, nouvel import, nouvelle classe/fonction/composant, nouvelle route) — sans LLM, donc silencieux sur les bugfixes/changements triviaux. Un même diff n'est signalé qu'une fois (pas de nag répété tant qu'il ne change pas).

Quand il détecte un changement potentiellement significatif, il injecte un rappel dans le contexte. **Si ce rappel apparaît, invoquer la skill `seeforce-arch-check` avant de considérer la tâche terminée** — elle compare l'état actuel des annotations C4 (via `mcp__seeforce__get_architecture_for_files`) à ce que le code fait réellement, et propose les corrections nécessaires. C'est un audit à froid, pas une relecture — les erreurs de ce type (relation inventée, edge manquante, description qui ne dit pas ce qui circule) sont typiquement invisibles en se relisant soi-même pendant qu'on écrit.

Le hook est une passe heuristique volontairement simple (aucun jugement sémantique) — elle ne remplace pas la question "avant tout changement important" ci-dessus, elle rattrape ce qui y échappe.

## Commentaires — 2 lignes maximum

Un commentaire de code (`#`, `//`) ne doit jamais dépasser 2 lignes — les docstrings (`"""..."""`, `/** ... */`) n'entrent pas dans cette règle, elles peuvent rester plus longues. Si une explication a besoin de plus de 2 lignes, c'est un signal qu'il faut soit simplifier le code pour qu'il se suffise à lui-même, soit déplacer le contexte dans la docstring du composant/de la fonction plutôt que dans un commentaire inline.

<!-- seeforce:arch-sync-section -->
## Keeping C4 architecture annotations in sync

### Before any important change

Before implementing a significant feature, new service, new module, or architectural shift, ask:

> "Does this change deserve to be documented in the C4 annotations (new Container, Component, or relation) so the architecture stays accurate?"

If yes, propose the C4 elements to add or update before writing code.

**Counts as "important":**
- New service or app (C4 Container)
- New distinct functional module (C4 Component)
- New external dependency (database, third-party API, auth provider)
- Change in communication protocol between components
- New boundary (bounded context, network zone, domain)

**Does NOT need a C4 update:**
- Bugfixes
- Internal refactoring within a component
- Cosmetic UI changes
- Adding fields to an existing model

### After a change — check for drift

A Stop hook (`.claude/hooks/arch-sync-check.sh`) runs automatically at the end of each turn. It looks only at uncommitted source files and checks for cheap structural signals (new file, new import, new class/function/component, new route) — no LLM, so it stays silent on bugfixes and trivial changes. The same diff is only flagged once, not re-nagged every turn.

When it detects a potentially significant change, it injects a reminder into context. **If that reminder appears, invoke the `seeforce-arch-check` skill before considering the task done** — it compares the current C4 annotation state (via `mcp__seeforce__get_architecture_for_files`) against what the code actually does, and proposes the necessary fixes.

The hook is a deliberately simple heuristic pass (no semantic judgment) — it doesn't replace the "before any important change" question above, it catches what slips through it.
