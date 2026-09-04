# Documentation NexTarget Server

## Démarrer et exploiter

- [Démarrage rapide](guides/quickstart.md) : environnement local, tests, OAuth et Coach.
- [Administration read-only](guides/admin-read-only.md) : génération de l'empreinte et activation de la page utilisateurs.
- [Déploiement Render](tech/render_setup.md) : variables, vérifications et incidents courants.
- [PostgreSQL Neon et Alembic](tech/postgres_neon_migration.md) : migration, sauvegarde, restauration et rollback.

## Comprendre

- [Architecture](tech/architecture.md) : responsabilités, routes, jetons, Coach, données et sécurité HTTP.
- [Notes de version](releases/) : historique synthétique par version.
- [CHANGELOG](../CHANGELOG.md) : historique détaillé.

Le backlog produit et la vue serveur sont maintenus uniquement dans NexTarget-app :

- [backlog unifié](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/backlog-unifie.md) ;
- [vue serveur](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/vue-serveur.md) ;
- [gouvernance](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/README.md).

Les anciens backlogs locaux, specs de profil, guides OAuth et snapshots OpenAPI ont été supprimés : ils dupliquaient le code ou décrivaient des comportements périmés. Le contrat HTTP courant est généré directement par FastAPI sur `/openapi.json` et `/docs`.

## Règles de maintenance

1. Documenter uniquement le comportement réellement présent dans `app/` et vérifié dans `tests/`.
2. Reporter les décisions produit dans le backlog canonique côté app, sans copie locale.
3. Mettre à jour l'architecture lorsqu'une route, une règle de jeton ou une responsabilité change.
4. Mettre à jour les procédures Render/PostgreSQL avec toute nouvelle variable ou migration.
5. Ne conserver aucun secret, hostname de base complet, token ou prompt complet dans la documentation.
