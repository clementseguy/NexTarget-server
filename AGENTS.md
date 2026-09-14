# AGENTS.md — NexTarget Server

Instructions pour les agents travaillant sur le serveur FastAPI de NexTarget.

## Projet et sources

- Python 3.11, FastAPI, SQLModel, Pydantic v1.
- SQLite en développement/tests ; PostgreSQL et Alembic en production.
- Responsabilités : OAuth/profil et proxy Coach IA authentifié.
- Code et docstrings en anglais ; documentation en français.
- Le backlog canonique vit dans `../NexTarget-app/docs/backlog/`. Pour une US :
  `bash ../NexTarget-app/scripts/us_context.sh NT-XXX`.

Lire uniquement la documentation utile à la tâche :

| Besoin | Référence |
|---|---|
| Architecture, routes, contrats, sécurité | `docs/tech/architecture.md` |
| Environnement local | `docs/guides/quickstart.md` |
| PostgreSQL et Alembic | `docs/tech/postgres_neon_migration.md` |
| Déploiement | `docs/tech/render_setup.md` |
| Administration | `docs/guides/admin-read-only.md` |

Le code, les tests et l'OpenAPI généré par FastAPI restent les références du
comportement exécuté. Ne créer aucun backlog ou snapshot OpenAPI local.

## Architecture

- Direction des dépendances : `api → core/services`; `models` et `schemas` sont
  des feuilles.
- Les handlers valident et orchestrent ; la logique métier, les prompts et les
  appels externes vivent dans `services/`.
- Toute configuration passe par `core/config.py` et les variables
  d'environnement.
- Les sessions DB sont injectées par `Depends(get_session)` et l'utilisateur
  courant par `Depends(get_current_user)`.

## Invariants de sécurité

- Authentification déléguée aux IdP : ne jamais ajouter de mot de passe local.
- Conserver state CSRF à usage unique, nonce OIDC Google et vérification du type
  des JWT.
- Les refresh tokens restent opaques, hashés, rotatifs et révocables par
  famille en cas de rejeu.
- Ne jamais exposer ni journaliser token, secret, URL DB complète, prompt
  complet ou query string sensible.
- Toute requête HTTP externe possède un timeout.
- Le Coach exige un JWT et conserve son rate limiting.
- Ne pas relâcher la politique CORS hors développement.
- `DATABASE_URL` utilise le rôle runtime sans DDL ;
  `DATABASE_MIGRATION_URL` est réservé aux migrations et à l'administration.
- Alembic est l'unique source du schéma PostgreSQL ; `create_all()` reste limité
  à SQLite.

## Code et tests

- Types sur les signatures publiques et docstrings Google style.
- Imports standard, tiers, locaux ; nommage Python conventionnel.
- Rester en Pydantic v1 (`Optional[T]`, `BaseSettings` depuis `pydantic`).
- Utiliser les fixtures de `tests/conftest.py`.
- Mocker systématiquement les IdP et Mistral ; aucun appel externe réel dans la
  suite automatisée.
- Toute logique ou route nouvelle reçoit un cas nominal et un cas d'erreur.
- Aucun émoji dans le code, les réponses API, la documentation ou Git.

## Validation

Pendant le développement, exécuter les tests ciblés. À la fin, lancer une seule
fois `pytest`. Ne pas répéter la suite complète sans modification du code. Les
tests PostgreSQL restent conditionnés par `NEXTARGET_TEST_POSTGRES_URL` comme
décrit dans la documentation technique.

## Livraison

- Flux Git : `main ← dev ← type/NT-XXX-slug` ; jamais de commit direct sur
  `main`.
- Une PR de feature vise `dev`. Inclure `NT-XXX` dans branche, commits et PR.
- Mettre à jour la documentation concernée et `CHANGELOG.md` lorsque requis.
- Les statuts et critères d'US se modifient uniquement dans le backlog de
  `NexTarget-app`.
- Préserver les changements utilisateur et ne jamais committer de secret.
