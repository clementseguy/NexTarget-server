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
2. **Proxy Coach IA** : `POST /coach/analyze-session` appelle Mistral côté serveur — la clé API et le prompt **ne transitent jamais par le client**. Multi-personas (`coach_neutre`, `coach_cool`), protégé par JWT et rate-limité.

## 🔌 API

| Endpoint | Rôle |
|---|---|
| `GET /health` | Health check |
| `GET /auth/google/login` → `GET /auth/google/callback` | Flow OAuth Google (state CSRF usage unique, **nonce OIDC vérifié**) |
| `GET /auth/facebook/start` → `GET /auth/facebook/callback` | Flow OAuth Facebook |
| `POST /auth/token/exchange` | Callback token → access token (+ refresh token) |
| `POST /auth/token/refresh` | Rotation du refresh token (usage unique, rejeu ⇒ révocation de famille) |
| `POST /auth/token/revoke` | Révocation (logout), 204 idempotent |
| `GET /users/me` · `PATCH /users/me/profile` | Profil utilisateur (JWT) |
| `POST /coach/analyze-session` | Analyse coach IA (JWT + rate limit 10/5 min) |

Swagger : `http://localhost:8000/docs` · Spec : [docs/nextarget-api-v0.1.0.yaml](docs/nextarget-api-v0.1.0.yaml)

## 🚀 Démarrage rapide

```bash
pip install -r requirements.txt
cp .env.example .env       # renseigner JWT_SECRET_KEY, Google OAuth, MISTRAL_API_KEY
uvicorn app.main:app --reload
```

📖 [Guide détaillé](docs/guides/quickstart.md) — flow OAuth testable en 5 minutes.

## 🔒 Sécurité

- Secrets **exclusivement** en variables d'environnement (`.env` local, Render en prod).
- State OAuth à usage unique (anti-CSRF) + vérification du **nonce OIDC** Google (anti-rejeu).
- Vérification stricte du type de JWT (`callback` ≠ `access`).
- Refresh tokens : hash SHA-256 seul persisté, rotation par famille, rejeu ⇒ révocation totale.
- CORS piloté par l'environnement : `*` en dev, **aucune origine** en prod sauf configuration explicite.
- Logs JSON structurés + corrélation `X-Request-ID` — jamais de token, clé ou prompt dans les logs.

Détails : [SECURITY_ANALYSIS.md](docs/reviews/SECURITY_ANALYSIS.md) · règles non négociables dans [AGENTS.md](AGENTS.md).

## 🧪 Tests & CI

```bash
pytest                     # 65 tests, providers OAuth entièrement mockés
pytest --cov=app           # couverture (~80 %)
```

CI GitHub Actions sur chaque push/PR : pytest + couverture (Python 3.11).

## ⚙️ Stack & déploiement

Python 3.11 · FastAPI · SQLModel · SQLite · PyJWT · httpx · Pydantic v1

Déploiement [Render.com](https://render.com) via [render.yaml](render.yaml) (branche `main`) — voir [docs/tech/render_setup.md](docs/tech/render_setup.md).

## 📚 Documentation

| Document | Contenu |
|---|---|
| [docs/guides/quickstart.md](docs/guides/quickstart.md) | Démarrage rapide |
| [docs/tech/architecture.md](docs/tech/architecture.md) | Architecture et flows OAuth |
| [docs/tech/render_setup.md](docs/tech/render_setup.md) | Déploiement Render |
| [docs/reviews/SECURITY_ANALYSIS.md](docs/reviews/SECURITY_ANALYSIS.md) | Analyse de sécurité |
| [docs/specs/vue-serveur.md](docs/specs/vue-serveur.md) | Projection du [backlog unifié](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/backlog-unifie.md) |
| [docs/releases/](docs/releases/) · [CHANGELOG.md](CHANGELOG.md) | Notes de version et historique |

---

<div align="center">
<sub>Application mobile : <a href="https://github.com/clementseguy/NexTarget-app">NexTarget-app</a> (Flutter)</sub>
</div>
