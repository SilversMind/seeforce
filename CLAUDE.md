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
