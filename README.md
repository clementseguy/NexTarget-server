<div align="center">

# NexTarget Server

**Backend de [NexTarget](https://github.com/clementseguy/NexTarget-app) — authentification OAuth et proxy Coach IA.**

[![CI](https://github.com/clementseguy/NexTarget-server/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/clementseguy/NexTarget-server/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/tag/clementseguy/NexTarget-server?label=release&color=14319b)](https://github.com/clementseguy/NexTarget-server/releases)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

</div>

---

Deux responsabilités, volontairement rien de plus :

1. **Authentification OAuth** déléguée à 100 % aux Identity Providers (Google, Facebook) — aucun mot de passe stocké. JWT courts (callback 10 min / access 60 min) + **refresh tokens avec rotation** et détection de rejeu.
2. **Coach de session** : `POST /coach/analyze-session` persiste à la demande la
   session identifiée par UUID, déduplique les analyses inchangées et appelle
   Mistral côté serveur pour un débrief structuré. La clé et le prompt ne
   transitent jamais par le client. Les variantes existantes
   (`coach_neutre`, `coach_cool`) restent protégées par JWT et rate-limitées.

## API

| Endpoint | Rôle |
|---|---|
| `GET /` | Page d’accueil publique et statique de NexTarget |
| `GET /health` | Health check |
| `GET /auth/google/login` → `GET /auth/google/callback` | Flow OAuth Google (state CSRF usage unique, **nonce OIDC vérifié**) |
| `GET /auth/facebook/start` → `GET /auth/facebook/callback` | Flow OAuth Facebook |
| `POST /auth/token/exchange` | Callback token → access token (+ refresh token) |
| `POST /auth/token/refresh` | Rotation du refresh token (usage unique, rejeu ⇒ révocation de famille) |
| `POST /auth/token/revoke` | Révocation (logout), 204 idempotent |
| `GET /users/me` · `PATCH /users/me/profile` | Profil utilisateur (JWT) |
| `POST /coach/analyze-session` | Débrief structuré et idempotent d'une session (JWT + rate limit 10/5 min) |
| `GET /app/admin/users` | Page HTML read-only des utilisateurs (hors API REST, HTTP Basic sur HTTPS) |

Swagger : `http://localhost:8000/docs` · OpenAPI courant : `http://localhost:8000/openapi.json`

## Démarrage rapide

```bash
pip install -r requirements.txt
cp .env.example .env       # renseigner JWT_SECRET_KEY, Google OAuth, MISTRAL_API_KEY
uvicorn app.main:app --reload
```

[Guide détaillé](docs/guides/quickstart.md).

## Sécurité

- Secrets **exclusivement** en variables d'environnement (`.env` local, Render en prod).
- State OAuth à usage unique (anti-CSRF) + vérification du **nonce OIDC** Google (anti-rejeu).
- Vérification stricte du type de JWT (`callback` ≠ `access`).
- Refresh tokens : hash SHA-256 seul persisté, rotation par famille, rejeu ⇒ révocation totale.
- CORS piloté par l'environnement : `*` en dev, **aucune origine** en prod sauf configuration explicite.
- Logs JSON structurés + corrélation `X-Request-ID` — jamais de token, clé ou prompt dans les logs.

Architecture et protections : [docs/tech/architecture.md](docs/tech/architecture.md) · règles non négociables dans [AGENTS.md](AGENTS.md).

## Tests & CI

```bash
pytest                     # 65 tests, providers OAuth entièrement mockés
pytest --cov=app           # couverture (~80 %)
```

CI GitHub Actions sur chaque push/PR : pytest + couverture (Python 3.11).

## Stack & déploiement

Python 3.11 · FastAPI · SQLModel · PostgreSQL en production · SQLite en local/tests · PyJWT · httpx · Pydantic v1

Déploiement [Render.com](https://render.com) via [render.yaml](render.yaml) (branche `main`) — voir [docs/tech/render_setup.md](docs/tech/render_setup.md).

## Documentation

| Document | Contenu |
|---|---|
| [docs/README.md](docs/README.md) | Index et règles de maintenance |
| [docs/guides/quickstart.md](docs/guides/quickstart.md) | Démarrage rapide |
| [docs/guides/admin-read-only.md](docs/guides/admin-read-only.md) | Administration read-only des utilisateurs |
| [docs/tech/architecture.md](docs/tech/architecture.md) | Architecture et flows OAuth |
| [docs/tech/render_setup.md](docs/tech/render_setup.md) | Déploiement Render |
| [Backlog unifié](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/backlog-unifie.md) | Inventaire et statut ; filtrer les portées `server` et `both` |
| [Descriptions des US](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/descriptions.md) | Définition fonctionnelle et critères d'acceptation |
| [Priorités](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/priorites.md) | Ordre de traitement courant |
| [Journal](https://github.com/clementseguy/NexTarget-app/tree/main/docs/backlog/journal) | Décisions et livraisons significatives |
| [Archives](https://github.com/clementseguy/NexTarget-app/tree/main/docs/backlog/archive) | US archivées par année d'archivage |
| [Gouvernance du backlog](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/README.md) | Statuts, journal et Definition of Done |
| [docs/releases/](docs/releases/) · [CHANGELOG.md](CHANGELOG.md) | Notes de version et historique |

---

<div align="center">
<sub>Application mobile : <a href="https://github.com/clementseguy/NexTarget-app">NexTarget-app</a> (Flutter)</sub>
</div>
