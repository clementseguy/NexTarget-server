# Démarrage rapide

## Environnement local

NexTarget-server utilise Python 3.11. Depuis la racine du dépôt :

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Remplacer au minimum `JWT_SECRET_KEY` dans `.env` par une valeur aléatoire. Sans `DATABASE_URL`, le serveur utilise `sqlite:///./data.db`, uniquement adapté au développement local.

Lancer ensuite :

```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health
pytest
```

L'API interactive et son contrat OpenAPI généré depuis le code sont disponibles sur `http://localhost:8000/docs` et `http://localhost:8000/openapi.json`. Aucun fichier OpenAPI statique n'est maintenu dans le dépôt.

## Activer Google OAuth en local

Déclarer dans `.env` :

```dotenv
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

La même URI doit être autorisée dans le client Web Google OAuth. Le parcours mobile est :

1. `GET /auth/google/login` renvoie `auth_url` et `state`.
2. Le navigateur ouvre `auth_url`.
3. Google revient sur `/auth/google/callback`.
4. Le serveur vérifie state, nonce et `id_token`, puis redirige vers `nextarget://callback?token=...`.
5. L'app échange ce jeton court via `POST /auth/token/exchange` et reçoit une paire access/refresh.

Le custom scheme n'est pas un parcours confortable à tester uniquement avec un navigateur de bureau. Pour une recette de bout en bout, utiliser l'app Flutter et le guide [serveur local avec l'émulateur Android](https://github.com/clementseguy/NexTarget-app/blob/main/docs/tech/serveur_local_emulateur_android.md).

## Activer le Coach

Définir `MISTRAL_API_KEY` dans `.env`. `POST /coach/analyze-session` exige un access token NexTarget ; les tests automatisés mockent toujours Mistral.

## Base PostgreSQL

Le développement quotidien et les tests unitaires utilisent SQLite. Les migrations PostgreSQL/Alembic et leur test dédié sont décrits dans [postgres_neon_migration.md](../tech/postgres_neon_migration.md).
