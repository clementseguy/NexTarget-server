# AGENTS.md — NexTarget Server

Instructions pour les agents de développement IA travaillant sur ce projet.

## Projet

Backend OAuth-only pour application mobile NexTarget. Authentification déléguée à 100% à des Identity Providers externes (Google, Facebook). Aucun mot de passe stocké, données utilisateur minimales (email + provider uniquement).

- **Stack** : Python 3.10+, FastAPI, SQLModel, SQLite (migration Postgres prévue), PyJWT, httpx
- **Version** : v0.1 — OAuth mobile flow fonctionnel
- **Déploiement** : Render.com (free tier), config dans `render.yaml`
- **Langue du code** : anglais (noms, docstrings, messages d'erreur)
- **Langue de la documentation** : français

## Architecture

```
app/
  main.py              # App FastAPI, CORS, routers, startup
  api/                 # Endpoints HTTP (couche présentation)
    auth_google.py     # OAuth Google (login, callback)
    auth_facebook.py   # OAuth Facebook (start, callback)
    auth_token.py      # Échange callback token → access token
    users.py           # Endpoints protégés (/users/me)
    deps.py            # Dépendances FastAPI (get_current_user)
    oauth_utils.py     # Code partagé OAuth (get_or_create_user, generate_token_response)
  core/                # Configuration et sécurité
    config.py          # Settings Pydantic (BaseSettings + .env)
    security.py        # Création/vérification JWT (callback + access tokens)
    oauth_config.py    # Constantes OAuth (endpoints, scopes, TTL)
  models/              # Modèles SQLModel (tables DB)
    user.py            # User(id, email, provider, is_active, created_at)
  schemas/             # Schémas Pydantic (API request/response)
    auth.py            # TokenResponse, UserPublic
  services/            # Logique métier et services
    database.py        # Engine SQLite, init_db(), get_session()
    oauth_state.py     # OAuthStateManager (state CSRF, TTL, one-time use)
tests/
  test_auth.py         # Tests pytest + httpx AsyncClient
docs/
  specs/               # Spécifications et backlog
  tech/                # Documentation technique (architecture, guides)
  reviews/             # Analyses de sécurité
  guides/              # Guides utilisateur (quickstart)
```

### Règles d'architecture

- **Direction des dépendances** : `api/ → core/` et `api/ → services/`, jamais l'inverse. `models/` et `schemas/` sont des feuilles sans dépendances latérales.
- **Un router par provider OAuth** : chaque IdP a son propre fichier dans `api/`. Le code commun va dans `oauth_utils.py`.
- **Configuration centralisée** : toute valeur configurable passe par `core/config.py` (Settings + `.env`). Ne jamais hardcoder de secrets, URLs ou durées.
- **Constantes OAuth** : endpoints, scopes et TTL dans `core/oauth_config.py` avec `Final`.

## Conventions de code

### Style

- Type annotations sur toutes les signatures de fonctions publiques
- Docstrings en anglais (Google style) sur les fonctions publiques et les classes
- Imports groupés : stdlib → third-party → local (`..core`, `..services`)
- `Optional[str]` (Pydantic v1 est utilisé, pas `str | None`)
- f-strings pour le formatage

### Nommage

- Fonctions et variables : `snake_case`
- Classes : `PascalCase`
- Constantes : `UPPER_SNAKE_CASE` avec `Final` type annotation
- Fichiers : `snake_case.py`
- Préfixes de router : `/auth/{provider}` pour OAuth, `/users` pour profil
- Tags FastAPI : `auth-google`, `auth-facebook`, `auth-token`, `users`

### Patterns établis

- **Settings** : singleton via `@lru_cache` dans `get_settings()`
- **DB session** : injectée via `Depends(get_session)` (generator with/yield)
- **Auth courante** : `Depends(get_current_user)` qui décode le JWT et charge le User
- **Provider OAuth** : vérifier la config avec `assert_provider_configured()` en début de handler
- **State CSRF** : `get_state_manager().create_state()` puis `verify_and_consume()` (one-time use)
- **Tokens JWT** : deux types distincts — `callback` (10 min, redirect mobile) et `access` (60 min, API calls). Toujours vérifier le champ `type` du payload.
- **Redirect mobile** : les callbacks OAuth redirigent vers `nextarget://callback?token=JWT` (custom scheme)

## Sécurité — Règles non négociables

Ces règles sont critiques. Ne jamais introduire de régression sur ces points.

1. **Aucun mot de passe** : ce backend est OAuth-only. Ne jamais ajouter d'authentification locale (email/password).
2. **State tokens usage unique** : chaque state CSRF doit être consommé (supprimé) après vérification. Jamais réutilisable.
3. **Vérification du type de token JWT** : toujours vérifier `payload["type"]` (`"access"` ou `"callback"`) avant d'accorder l'accès. Un callback token ne doit jamais servir de token d'accès.
4. **Vérification id_token Google** : utiliser la lib officielle `google-auth` pour vérifier signature, audience, issuer et expiration.
5. **Timeout sur les requêtes HTTP externes** : toujours utiliser `timeout=OAUTH_TIMEOUT_SECONDS` (15s) pour les appels vers Google/Facebook.
6. **Secrets en variables d'environnement** : jamais de secret dans le code source. Tout passe par `Settings` + `.env`.
7. **Pas d'info interne dans les erreurs HTTP** : ne pas exposer de stack traces, noms de tables, ou détails d'implémentation dans les réponses d'erreur vers le client.
8. **CORS** : `allow_origins=["*"]` est un TODO connu (acceptable en dev, à restreindre en prod). Ne pas élargir d'autres paramètres CORS.

## Tests

- **Framework** : pytest + httpx `AsyncClient` + `anyio`
- **Config** : `pytest.ini` → `asyncio_mode = auto`, `pythonpath = .`
- **Lancement** : `pytest -q` depuis la racine
- **Fixture DB** : `reset_db()` (autouse) → drop_all + create_all entre chaque test
- **Pattern de test endpoint** : `async with AsyncClient(app=app, base_url="http://test") as ac:`
- **OAuth non configuré** : les tests gèrent le cas où les env vars OAuth sont absentes (assertion sur `"not configured"`)
- Pour tout nouveau endpoint ou modification de logique : ajouter un test. Minimum : cas nominal + cas d'erreur.
- Les tests de flow OAuth complet nécessitent des mocks des providers externes (à faire en v0.2+).

## Décisions intentionnelles

Ne pas "corriger" ces points — ce sont des choix délibérés pour la v0.1 :

- **SQLite** comme base de données (migration Postgres via Alembic planifiée v0.2)
- **State OAuth en mémoire** (`OAuthStateManager` dict in-process). Suffisant pour single-instance. Redis planifié pour multi-instance.
- **Pas de refresh tokens** : prévu pour v0.2
- **Pas de rate limiting** : prévu pour v0.2 (Redis/nginx)
- **Pas de logging structuré** : prévu pour v0.2 (OpenTelemetry)
- **Pydantic v1** (via `pydantic==1.10.x` et `BaseSettings` dans pydantic directement, pas `pydantic-settings`)
- **`@app.on_event("startup")`** : legacy FastAPI, migration vers lifespan possible mais non prioritaire
- **Nonce Google généré mais non vérifié** dans le callback : amélioration identifiée dans `SECURITY_ANALYSIS.md`

## Roadmap v0.2 (contexte pour les agents)

Prévisions pour les prochaines itérations (ne pas implémenter proactivement) :

- Refresh tokens + rotation
- Rate limiting (Redis ou middleware)
- Logging structuré JSON + tracing OpenTelemetry
- Migration Postgres + Alembic
- Apple Sign In
- Tests OAuth mockés (providers externes)
- Restriction CORS par environnement

## Commandes de référence

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur (dev)
uvicorn app.main:app --reload --port 8000

# Lancer les tests
pytest -q

# Health check
curl http://localhost:8000/health

# Documentation interactive
# Ouvrir http://localhost:8000/docs
```

## Documentation de référence

- [docs/tech/architecture.md](docs/tech/architecture.md) — Architecture complète du flow OAuth mobile
- [docs/reviews/SECURITY_ANALYSIS.md](docs/reviews/SECURITY_ANALYSIS.md) — Analyse de sécurité et points à améliorer
- [docs/specs/Backlog v0.1.md](docs/specs/Backlog%20v0.1.md) — Périmètre et statut des tâches v0.1
- [docs/guides/quickstart.md](docs/guides/quickstart.md) — Guide de démarrage rapide
- [CHANGELOG.md](CHANGELOG.md) — Historique des changements