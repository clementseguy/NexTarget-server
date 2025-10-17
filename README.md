# NexTarget Server

Backend léger pour application mobile : FastAPI + SQLite + JWT + OAuth (Google, Facebook).

## Fonctionnalités
- Authentification locale (email / mot de passe, hash bcrypt)
- Providers OAuth externes : Google & Facebook (implémentés v0.1)
- JWT bearer tokens (access tokens)
- Endpoint protégé `/users/me`
- Base SQLite via SQLModel (migration future possible vers Postgres)
- Configuration par variables d'environnement (.env)

## Démarrage rapide
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # puis éditez les valeurs
uvicorn app.main:app --reload
```
Visitez http://127.0.0.1:8000/docs pour la doc interactive.

## Endpoints principaux (v0.1)
Auth :
- POST /auth/register (provider=local|google|facebook) – password requis si local
- POST /auth/login (provider=local)
- GET /users/me
- GET /auth/google/start
- GET /auth/google/callback
- GET /auth/facebook/start
- GET /auth/facebook/callback

## Sécurité / Production
- Générer une vraie clé aléatoire pour `JWT_SECRET_KEY`
- Restreindre CORS (liste d'origines précises)
- Activer HTTPS (terminaison TLS via reverse proxy ou plateforme)
- Ajouter rate-limiting (ex: Traefik, nginx, ou lib python)
- Stocker les mots de passe toujours hashés (déjà fait) ; jamais en clair
- Logs structurés (peut ajouter `uvicorn[standard]` déjà inclus) et monitoring

## Déploiement minimal
Peut tourner sur :
- VM (1 vCPU / 512MB) : `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Fly.io / Railway / Render / Deta : ajouter un Dockerfile ou config native.

### Exemple Docker
```Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Tests
Exécution :
```bash
pytest -q
```
Couverture actuelle :
- Authentification locale + providers (unicité email+provider)

Améliorations futures tests :
- Tests d'intégration Google & Facebook OAuth (mock token endpoints)

## Roadmap v0.1 (résumé)
Done : Auth locale + OAuth (Google, Facebook), JWT, tests de base.
À venir (v0.2+) :
- Refresh tokens / rotation
- Politique mots de passe forts (zxcvbn ou règles dynamiques)
- Rate limiting robuste (Redis / nginx / envoy)
- Sécurité brute-force (compteur + backoff)
- Logging structuré + tracing (OpenTelemetry)
- Passage Postgres + migrations (Alembic)
- Observabilité (metrics Prometheus)

## Intégrations OAuth
### Google
Flux:
1. /auth/google/start : `state` + `nonce` -> URL consent
2. /auth/google/callback : échange code -> tokens (Google), vérifie id_token (aud, iss, exp)
3. Upsert user provider=google (password None)
4. Retour JWT interne

Env :
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://votre-domaine/auth/google/callback
```

### Facebook
Flux:
1. /auth/facebook/start : génère `state`, URL consent (scope email)
2. /auth/facebook/callback : échange code -> access_token, GET /me (id,email)
3. Upsert user provider=facebook (email fallback si non fourni)
4. Retour JWT interne

Env :
```
FACEBOOK_CLIENT_ID=...
FACEBOOK_CLIENT_SECRET=...
FACEBOOK_REDIRECT_URI=https://votre-domaine/auth/facebook/callback
```

## Architecture rapide
- couche api/: routers FastAPI
- couche models/: SQLModel ORM
- couche schemas/: Pydantic I/O

## Qualité & Sécurité
- Hash bcrypt (cost 12)
- Token JWT HS256 (prévoir rotation / secret fort)
- CORS permissif en dev (restreindre en prod)
- OAuth state validation (CSRF protection)


---
License: MIT (à préciser si souhaité)
