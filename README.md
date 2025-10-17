# NexTarget Server

Backend léger pour application mobile : FastAPI + SQLite + OAuth (Google, Facebook) uniquement.

## Fonctionnalités
- **Authentification OAuth uniquement** : Google & Facebook
- **Aucun stockage de mot de passe** : délégation complète à des IdP externes
- **Aucune donnée personnelle sensible** : email et provider uniquement
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
Santé :
- GET /health

Auth OAuth :
- GET /auth/google/start
- GET /auth/google/callback
- GET /auth/facebook/start
- GET /auth/facebook/callback

Profil :
- GET /users/me (JWT requis)

## Sécurité / Production
- **Aucun stockage de mot de passe** : authentification déléguée à 100% aux IdP
- **Données minimales** : seuls email et provider sont stockés
- Générer une vraie clé aléatoire pour `JWT_SECRET_KEY`
- Restreindre CORS (liste d'origines précises)
- Activer HTTPS (terminaison TLS via reverse proxy ou plateforme)
- Ajouter rate-limiting (ex: Traefik, nginx, ou lib python)
- Logs structurés et monitoring

## Déploiement sur Render.com (Recommandé)

### ✅ Pourquoi Render.com ?
- **HTTPS automatique** (Let's Encrypt)
- **Déploiement automatique** depuis GitHub
- **Gratuit** pour petits projets (avec sleep mode)
- **Variables d'environnement** sécurisées
- **Logs persistants** (14 jours)

### 🚀 Déploiement en 5 minutes

1. **Préparer le repository**
   ```bash
   # Le fichier render.yaml est déjà configuré
   git push origin main
   ```

2. **Créer le service sur Render**
   - Aller sur [render.com](https://render.com)
   - "New" → "Web Service"
   - Connecter votre repository GitHub `NexTarget-server`
   - Render détectera automatiquement `render.yaml`
   - Cliquer "Apply" pour créer le service

3. **Configurer les variables OAuth** (Dashboard Render)
   ```
   GOOGLE_CLIENT_ID=votre_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxx
   GOOGLE_REDIRECT_URI=https://votre-app.onrender.com/auth/google/callback
   
   FACEBOOK_CLIENT_ID=xxx
   FACEBOOK_CLIENT_SECRET=xxx
   FACEBOOK_REDIRECT_URI=https://votre-app.onrender.com/auth/facebook/callback
   ```
   
   Note: `JWT_SECRET_KEY` est généré automatiquement par Render

4. **Mettre à jour les OAuth Providers**
   - **Google Cloud Console** → OAuth 2.0 Client IDs → Authorized redirect URIs
     ```
     https://votre-app.onrender.com/auth/google/callback
     ```
   - **Facebook App Dashboard** → Settings → Basic → Valid OAuth Redirect URIs
     ```
     https://votre-app.onrender.com/auth/facebook/callback
     ```

5. **Vérifier le déploiement**
   ```bash
   # Health check
   curl https://votre-app.onrender.com/health
   # Doit retourner: {"status":"ok"}
   
   # Documentation interactive
   # Ouvrir: https://votre-app.onrender.com/docs
   ```

### ⚠️ Limitations Free Tier
- **Sleep après 15min** d'inactivité (réveil en ~30s)
- **512MB RAM**, CPU partagé
- Suffisant pour 1-5 utilisateurs sporadiques

### 📈 Upgrade Production (optionnel)
Si besoin de plus de performance :
- $7/mois → Service toujours actif (no sleep)
- 1GB RAM, meilleure réactivité

### 🔍 Monitoring
Render Dashboard fournit :
- Logs en temps réel
- Métriques CPU/RAM
- Historique des déploiements

---

## Autres options de déploiement

### Déploiement manuel (VM)
```bash
# Sur serveur Linux
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Déploiement Docker
```Dockerfile
FROM python:3.9-slim
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
- Test basique du health endpoint

Améliorations futures tests :
- Tests d'intégration Google & Facebook OAuth (mock token endpoints et id_token verification)

## Roadmap v0.1 (résumé)
Done : Auth OAuth uniquement (Google, Facebook), JWT, stockage minimal (email + provider).
À venir (v0.2+) :
- Refresh tokens / rotation
- Rate limiting robuste (Redis / nginx / envoy)
- Logging structuré + tracing (OpenTelemetry)
- Passage Postgres + migrations (Alembic)
- Observabilité (metrics Prometheus)
- Tests automatisés OAuth (mock providers)

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
- couche api/: routers FastAPI (auth OAuth, users)
- couche services/: database session management
- couche models/: SQLModel ORM (User uniquement)
- couche schemas/: Pydantic I/O (TokenResponse, UserPublic)

## Qualité & Sécurité
- Pas de stockage de mot de passe
- Token JWT HS256 (prévoir rotation / secret fort)
- CORS permissif en dev (restreindre en prod)
- Authentification déléguée à 100% (Google, Facebook)


---
License: MIT (à préciser si souhaité)
