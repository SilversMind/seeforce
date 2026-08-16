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
