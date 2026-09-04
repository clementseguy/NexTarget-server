# Déploiement Render

Le blueprint [render.yaml](../../render.yaml) configure le build, la branche `main`, la région Frankfurt et les variables du service. La commande de démarrage Render doit être `python start.py` : elle applique d'abord `alembic upgrade head`, puis lance Uvicorn sur le port fourni par Render. Le blueprint ne déclare actuellement pas cette commande ; elle doit donc être vérifiée dans le Dashboard Render.

## Variables obligatoires

| Variable | Usage |
|---|---|
| `JWT_SECRET_KEY` | signature des JWT ; générée par le blueprint |
| `DATABASE_URL` | connexion PostgreSQL poolée du rôle applicatif sans DDL |
| `DATABASE_MIGRATION_URL` | connexion PostgreSQL directe du rôle propriétaire |
| `GOOGLE_CLIENT_ID` | client Web OAuth Google |
| `GOOGLE_CLIENT_SECRET` | secret OAuth Google |
| `GOOGLE_REDIRECT_URI` | callback HTTPS exact du déploiement |
| `MISTRAL_API_KEY` | appels Coach côté serveur |

Les deux URLs PostgreSQL, les secrets OAuth et la clé Mistral sont déclarés `sync: false` et doivent être saisis dans le Dashboard Render. Ne jamais les copier dans Git ni dans les logs.

Facebook reste facultatif et nécessite les trois variables `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET` et `FACEBOOK_REDIRECT_URI`.

L'administration read-only reste désactivée tant que `ADMIN_USERNAME` et `ADMIN_PASSWORD_HASH` ne sont pas tous deux définis. Voir [admin-read-only.md](../guides/admin-read-only.md).

## Valeurs pilotées par le blueprint

- `ENVIRONMENT=production`
- `DEBUG=false`
- `ACCESS_TOKEN_EXP_MINUTES=60`
- modèle et URL de base Mistral

En production, aucune origine navigateur CORS n'est autorisée par défaut. Définir `CORS_ALLOW_ORIGINS` uniquement si un client Web réel doit appeler l'API ; l'app native n'en a pas besoin.

## Vérifications après déploiement

```bash
curl https://nextarget-server.onrender.com/health
curl https://nextarget-server.onrender.com/openapi.json
```

Vérifier ensuite un flow Google depuis l'app, le renouvellement de session, une analyse Coach et l'accès HTTPS à `/app/admin/users` si l'administration est activée.

## Incidents courants

- Échec de migration : le service ne démarre pas. Vérifier séparément `DATABASE_MIGRATION_URL`, les droits du rôle propriétaire et la révision Alembic, sans journaliser l'URL.
- Erreur de base au runtime : vérifier `DATABASE_URL` et les droits lecture/écriture du rôle applicatif ; ne pas lui accorder de DDL.
- `redirect_uri_mismatch` : la valeur Render, l'URI Google autorisée et la route `/auth/google/callback` doivent être identiques.
- Provider non configuré : vérifier la présence des trois variables du provider.
- Coach indisponible : vérifier `MISTRAL_API_KEY`, le modèle, la disponibilité Mistral et les réponses 401/429 avant de modifier le code.

Les procédures de création, sauvegarde, restauration et rollback PostgreSQL sont dans [postgres_neon_migration.md](postgres_neon_migration.md).
