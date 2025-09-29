# NexTarget Server

Backend léger pour application mobile : FastAPI + SQLite + JWT + Mistral.

## Fonctionnalités
- Authentification par email / mot de passe (hash bcrypt)
- JWT bearer tokens (access tokens)
- Endpoints protégés (/users/me, /ai/completions)
- Appel API Mistral (chat completion)
- Base SQLite simple via SQLModel
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

## Endpoints principaux
- POST /auth/register
- POST /auth/login
- GET /users/me (Bearer token requis)
- POST /ai/completions (Bearer token + clé Mistral)

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

## Tests (à créer)
Un dossier `tests` est prêt pour accueillir les tests pytest.

## Prochaines améliorations
- Refresh tokens / rotation
- Politique mots de passe forts
- Limitation de requêtes / anti brute-force
- Logging + tracing (OpenTelemetry)
- Streaming des réponses Mistral
- Support Postgres (remplacer URL DB)

---
License: MIT (à préciser si souhaité)
