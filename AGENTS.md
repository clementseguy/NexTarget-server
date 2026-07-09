# AGENTS.md — NexTarget Server

Instructions pour les agents de développement IA travaillant sur ce dépôt.
Objectif : code cohérent avec l'existant et **qualité élevée** (ce repo doit
pouvoir être partagé sans réserve).

## Projet

Backend de l'app mobile NexTarget. Deux responsabilités :

1. **Authentification OAuth** déléguée à 100 % à des Identity Providers externes
   (Google, Facebook). Aucun mot de passe stocké.
2. **Proxy Coach IA** : endpoint `POST /coach/analyze-session` qui appelle Mistral
   côté serveur, pour que la **clé API et le prompt ne transitent jamais par le
   client**. Protégé par JWT (« coach connecté uniquement ») et rate-limité.

> ⚠️ Ce backend **n'est plus « OAuth-only sans IA »** : cette description
> historique (ancien `Backlog v0.1`) est périmée. La brique Coach IA fait
> pleinement partie du serveur.

- **Stack** : Python **3.11**, FastAPI, SQLModel, SQLite (Postgres prévu), PyJWT, httpx, Pydantic **v1**
- **Coach IA** : Mistral via httpx (`mistral_api_base`, `mistral_model` configurables)
- **Déploiement** : Render.com (free tier, région Frankfurt), config dans `render.yaml`
- **Langue du code** : anglais (noms, docstrings, messages d'erreur)
- **Langue de la documentation** : français

## Source de vérité produit

Le **quoi/pourquoi** vit dans le backlog unifié, hébergé dans le repo
**NexTarget-app** (pas ici) :

- **Backlog unifié (source de vérité)** : `NexTarget-app/docs/backlog/backlog-unifie.md`
- **Vue serveur (projection locale)** : [`docs/specs/vue-serveur.md`](docs/specs/vue-serveur.md)
- **Gouvernance / DoD / convention d'IDs** : `NexTarget-app/docs/backlog/README.md`

Ce repo ne maintient plus de backlog propre ; `docs/specs/Backlog v0.1.md` est un
simple pointeur, et l'ancien contenu est archivé sous `docs/specs/_archive/`.
En cas de conflit sur le périmètre produit, **le backlog prime** ; cet `AGENTS.md`
fait autorité sur le **comment**.

## Architecture

```
app/
  main.py              # App FastAPI, CORS, routers, startup (init_db)
  api/                 # Endpoints HTTP (couche présentation)
    auth_google.py     # OAuth Google (login, callback)
    auth_facebook.py   # OAuth Facebook (start, callback)
    auth_token.py      # Échange callback token → access token
    users.py           # Endpoints protégés (/users/me)
    coach.py           # Coach IA : POST /coach/analyze-session (proxy Mistral, JWT)
    deps.py            # Dépendances FastAPI (get_current_user)
    oauth_utils.py     # Code partagé OAuth (get_or_create_user, token response)
  core/
    config.py          # Settings Pydantic (BaseSettings + .env) — inclut la config Mistral
    security.py        # Création/vérification JWT (callback + access)
    oauth_config.py    # Constantes OAuth (endpoints, scopes, TTL) en Final
  models/
    user.py            # User(id, email, provider, is_active, created_at + profil)
  schemas/
    auth.py            # TokenResponse, UserPublic
    coach.py           # SessionIn/SeriesIn, AnalyzeSessionRequest/Response
  services/
    database.py        # Engine SQLite, init_db(), get_session()
    oauth_state.py     # OAuthStateManager (state CSRF, TTL, usage unique)
    mistral_client.py  # Appel HTTP Mistral (timeout, mapping d'erreurs)
    prompt_builder.py  # Assemble le prompt à partir de SessionIn + template YAML
    rate_limiter.py    # Rate limiting en mémoire (fenêtre glissante par user)
  prompts/
    coach_neutre.yaml  # Template de prompt (persona « neutre »)
    coach_cool.yaml    # Template de prompt (persona « cool », NT-032)
tests/
  test_auth.py         # Tests OAuth / users
  test_coach.py        # Tests endpoint coach
docs/
  specs/               # vue-serveur (projection backlog), pointeur backlog, _archive
  tech/                # Architecture, guides OAuth, setup Render
  reviews/             # SECURITY_ANALYSIS.md
  guides/              # quickstart
```

### Règles d'architecture
- **Direction des dépendances** : `api/ → core/` et `api/ → services/`, jamais l'inverse. `models/` et `schemas/` sont des feuilles.
- **Un router par provider OAuth** ; le commun va dans `oauth_utils.py`.
- **Coach** : le endpoint (`api/coach.py`) orchestre, la logique vit dans `services/` (`prompt_builder`, `mistral_client`, `rate_limiter`). Ne pas mettre d'appel réseau ou d'assemblage de prompt dans la couche `api/`.
- **Configuration centralisée** : toute valeur configurable passe par `core/config.py` (`Settings` + `.env`). Jamais de secret, URL ou durée en dur.
- **Constantes OAuth** dans `core/oauth_config.py` avec `Final`.

## Modèle de données

`User` (SQLModel, table) — clés : `id` (UUID), `email`, `provider`
(`google`/`facebook`), `is_active`, `created_at`, contrainte d'unicité composite
`(email, provider)`. **Profil** (rempli depuis l'IdP + choix utilisateur) :
`display_name`, `display_name_custom`, `avatar_url`, `experience_level`
(`beginner|advanced|expert`). **Toujours pas de `hashed_password`** : l'auth reste
100 % déléguée aux IdP.

## Conventions de code

### Style
- Type annotations sur toutes les signatures publiques.
- Docstrings en anglais (Google style) sur fonctions/classes publiques.
- Imports groupés : stdlib → third-party → local (`..core`, `..services`).
- **Pydantic v1** : `Optional[str]` (pas `str | None`), `BaseSettings` importé depuis `pydantic` (pas `pydantic-settings`).
- f-strings pour le formatage.

### Nommage
- `snake_case` (fonctions/variables), `PascalCase` (classes), `UPPER_SNAKE_CASE` + `Final` (constantes), `snake_case.py` (fichiers).
- Préfixes de router : `/auth/{provider}` (OAuth), `/users` (profil), `/coach` (IA).
- Tags FastAPI : `auth-google`, `auth-facebook`, `auth-token`, `users`, `coach`.

### Patterns établis
- **Settings** : singleton via `@lru_cache` dans `get_settings()`.
- **DB session** : injectée via `Depends(get_session)` (generator with/yield).
- **Auth courante** : `Depends(get_current_user)` (décode le JWT, charge le `User`).
- **Provider OAuth** : vérifier la config (`assert_provider_configured()`) en début de handler.
- **State CSRF** : `create_state()` puis `verify_and_consume()` (usage unique).
- **Tokens JWT** : deux types — `callback` (10 min, redirect mobile) et `access` (60 min, API). Toujours vérifier `payload["type"]`.
- **Redirect mobile** : les callbacks OAuth redirigent vers `nextarget://callback?token=JWT`.
- **Coach** : dans le handler, ordre = `rate_limiter.allow(user.id)` → `build_prompt(...)` (422 si variante inconnue) → `mistral_client.fetch_analysis(...)` (mapping d'erreurs) → réponse typée.

## Sécurité — Règles non négociables

Critiques. Ne jamais introduire de régression.

1. **Aucun mot de passe** : backend OAuth-only côté auth. Ne jamais ajouter d'auth locale (email/password).
2. **State tokens usage unique** : chaque state CSRF est consommé (supprimé) après vérification.
3. **Vérification du type de token JWT** : toujours vérifier `payload["type"]` (`access`/`callback`). Un callback token ne donne jamais accès à l'API.
4. **Vérification `id_token` Google** via la lib officielle `google-auth` (signature, audience, issuer, expiration) **+ vérification du nonce OIDC** contre celui stocké avec le state (NT-066) — ne jamais retirer ce contrôle.
5. **Timeouts** sur toute requête HTTP externe : `OAUTH_TIMEOUT_SECONDS` (15 s) pour les IdP ; `mistral_timeout_seconds` (30 s) pour Mistral.
6. **Secrets en variables d'environnement** uniquement (`Settings` + `.env`). Jamais dans le code. Sur Render, les secrets sont `sync: false` (définis à la main) — inclut `MISTRAL_API_KEY`.
7. **Coach = données minimales + protégé** : l'endpoint exige un JWT (`get_current_user`). Ne jamais renvoyer au client la clé Mistral **ni le prompt complet**, et ne pas les logguer. Le client n'envoie que les données de session.
8. **Rate limiting sur les endpoints coûteux** (appels Mistral) : conserver `coach_rate_limiter` (429 au-delà). Ne pas exposer un endpoint IA sans limite.
9. **Pas d'info interne dans les erreurs HTTP** : pas de stack trace, nom de table ou détail d'implémentation vers le client.
10. **CORS** : origines pilotées par l'environnement (NT-065, `Settings.cors_origins`) — `*` en dev, **aucune origine** hors dev sauf `CORS_ALLOW_ORIGINS` explicite. Ne pas relâcher ce comportement ni élargir les autres paramètres CORS.

## Tests

- **Framework** : pytest + httpx `AsyncClient` + `anyio`. Config `pytest.ini` (`asyncio_mode = auto`, `pythonpath = .`, `-q`).
- **Lancement** : `pytest` depuis la racine.
- **Fixture DB** : `reset_db()` (autouse) → drop_all + create_all entre chaque test.
- **Pattern endpoint** : `async with AsyncClient(app=app, base_url="http://test") as ac:`.
- **Coach** : mocker `mistral_client.fetch_analysis` (ne jamais appeler la vraie API Mistral dans les tests) ; couvrir 200, 401 (non authentifié), 422 (variante inconnue), 429 (rate limit).
- **OAuth non configuré** : les tests gèrent l'absence des env vars OAuth (assertion `"not configured"`).
- Tout nouveau endpoint ou changement de logique → test : **cas nominal + cas d'erreur** au minimum.

## Avant de committer (checklist)

1. `pytest` vert.
2. Toute nouvelle valeur configurable passée par `core/config.py` (+ `.env.example` mis à jour).
3. Aucune régression sur les règles de sécurité ci-dessus ; aucun secret dans le diff.
4. `CHANGELOG.md` mis à jour ; statut de l'item mis à jour dans le backlog unifié (+ recopie dans `docs/specs/vue-serveur.md`).

## Workflow Git (rappel gouvernance)

- **Branche par item** : `type/NT-XXX-slug` (ex. `feat/NT-066-verif-nonce-google`).
- **Commit** : sujet préfixé par l'ID — `feat(coach): NT-032 persona coach cool`.
- **PR** : titre `[NT-XXX] …`, corps listant les IDs + critères cochés.
- Un item `both` peut donner une PR ici **et** une dans NexTarget-app, avec le **même ID**.
- **Definition of Done** : voir `NexTarget-app/docs/backlog/README.md`.

## Décisions intentionnelles (ne pas « corriger »)

- **SQLite** (migration Postgres/Alembic planifiée — backlog NT-071).
- **State OAuth ET rate limiter en mémoire** (dict/deque in-process) : suffisant en single-instance. Redis nécessaire pour le multi-instance (lié à NT-071).
- **Pas de refresh tokens** (backlog NT-048).
- **Pas de logging structuré / tracing** encore (backlog NT-053).
- **Pydantic v1** (`pydantic==1.10.x`, `BaseSettings` dans `pydantic`).
- **`@app.on_event("startup")`** : legacy FastAPI, migration vers lifespan non prioritaire.

## Commandes de référence

```bash
pip install -r requirements.txt              # dépendances
uvicorn app.main:app --reload --port 8000    # serveur (dev)
pytest                                        # tests
curl http://localhost:8000/health            # health check
# Doc interactive : http://localhost:8000/docs
```

## Documentation de référence
- [`docs/specs/vue-serveur.md`](docs/specs/vue-serveur.md) — projection serveur du backlog unifié
- [`docs/tech/architecture.md`](docs/tech/architecture.md) — flow OAuth mobile
- [`docs/reviews/SECURITY_ANALYSIS.md`](docs/reviews/SECURITY_ANALYSIS.md) — analyse de sécurité et points à améliorer
- [`docs/guides/quickstart.md`](docs/guides/quickstart.md) — démarrage rapide
- [`CHANGELOG.md`](CHANGELOG.md) — historique des changements
