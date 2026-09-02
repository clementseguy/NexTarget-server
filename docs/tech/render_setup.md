# Configuration Render.com - Variables d'Environnement

## 🔧 Variables à Configurer sur Render Dashboard

### 1. Variables Automatiques (déjà dans render.yaml)
Ces variables sont configurées automatiquement au premier déploiement :

| Variable | Valeur | Description |
|----------|--------|-------------|
| `ACCESS_TOKEN_EXP_MINUTES` | `60` | Durée validité JWT (minutes) |
| `ENVIRONMENT` | `production` | Environnement |
| `DEBUG` | `false` | Mode debug désactivé |
| `JWT_SECRET_KEY` | *auto-généré* | Clé secrète JWT (256 bits) |

---

### 2. Base de Données PostgreSQL (Neon) — NT-071

**IMPORTANT** : `DATABASE_URL` et `DATABASE_MIGRATION_URL` sont déclarées dans
`render.yaml` avec `sync: false` : elles **doivent être saisies manuellement**
dans le Dashboard Render (onglet Environment), jamais commitées.

| Variable | Rôle Neon | Connexion | Usage |
|----------|-----------|-----------|-------|
| `DATABASE_URL` | `nextarget_app` (privilèges minimaux) | poolée (`-pooler`) | Runtime de l'application |
| `DATABASE_MIGRATION_URL` | `neondb_owner` | directe (unpooled) | Alembic (migrations) + `pg_dump` |

Procédure complète (création du projet Neon, des rôles, bascule, sauvegarde,
restauration, rollback) : voir
[`docs/tech/postgres_neon_migration.md`](postgres_neon_migration.md).

---

### 3. Variables OAuth à Ajouter Manuellement

⚠️ **IMPORTANT** : Ces variables doivent être ajoutées via le Dashboard Render avant le premier déploiement.

#### Google OAuth

1. **Obtenir les credentials** :
   - Aller sur [Google Cloud Console](https://console.cloud.google.com)
   - Créer un projet ou en sélectionner un
   - Activer "Google+ API"
   - Credentials → Create Credentials → OAuth 2.0 Client ID
   - Type : Web application
   - Authorized redirect URIs : `https://votre-app.onrender.com/auth/google/callback`

2. **Variables à ajouter** :
   ```
   GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
   GOOGLE_REDIRECT_URI=https://votre-app.onrender.com/auth/google/callback
   ```

#### Facebook OAuth

1. **Obtenir les credentials** :
   - Aller sur [Facebook Developers](https://developers.facebook.com)
   - My Apps → Create App → Consumer
   - Settings → Basic
   - Add Platform → Website
   - Valid OAuth Redirect URIs : `https://votre-app.onrender.com/auth/facebook/callback`

2. **Variables à ajouter** :
   ```
   FACEBOOK_CLIENT_ID=1234567890123456
   FACEBOOK_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   FACEBOOK_REDIRECT_URI=https://votre-app.onrender.com/auth/facebook/callback
   ```

---

## 📝 Procédure d'Ajout sur Render

### Configuration Initiale Requise

⚠️ **IMPORTANT** : Après le premier déploiement, configurer dans le Dashboard Render :

1. **Start Command** (Settings → Build & Deploy)
   - Valeur : `python start.py`
   - Cette commande est **requise** pour que le service bind correctement sur `0.0.0.0:$PORT`

2. **Python Version** (détecté automatiquement)
   - Fichier `.python-version` à la racine définit la version : `3.11.9`
   - Nécessaire pour compatibilité avec Pydantic v1

### Variables d'Environnement OAuth (Recommandé)

1. Aller sur votre service Render
2. Onglet **"Environment"**
3. Cliquer **"Add Environment Variable"**
4. Pour chaque variable :
   - **Key** : nom de la variable (ex: `GOOGLE_CLIENT_ID`)
   - **Value** : valeur de la variable
   - Cocher **"Secret"** pour les credentials sensibles
5. Cliquer **"Save Changes"**
6. Le service redémarre automatiquement

### Via render.yaml (Pour info uniquement)

Les variables sont déjà déclarées dans `render.yaml` avec `sync: false`, ce qui signifie qu'elles doivent être définies manuellement et ne seront pas écrasées lors des redéploiements.

**Note** : La propriété `startCommand` dans `render.yaml` est ignorée par Render. Utilisez le Dashboard UI.

### Administration read-only (NT-049)

Définir `ADMIN_USERNAME` et `ADMIN_PASSWORD_HASH` comme secrets dans le
Dashboard. `ADMIN_PASSWORD_HASH` contient une empreinte scrypt salée générée
localement, jamais le mot de passe brut. La génération et le test d’accès sont
documentés dans [`docs/guides/admin-read-only.md`](../guides/admin-read-only.md).

---

## 🔍 Vérification Post-Déploiement

### 1. Tester le Health Check
```bash
curl https://votre-app.onrender.com/health
# Attendu: {"status":"ok"}
```

### 2. Vérifier la Configuration OAuth
```bash
# Google
curl https://votre-app.onrender.com/auth/google/start
# Attendu: {"auth_url":"https://accounts.google.com/...", "state":"..."}

# Facebook  
curl https://votre-app.onrender.com/auth/facebook/start
# Attendu: {"auth_url":"https://www.facebook.com/...", "state":"..."}
```

Si erreur `"Google/Facebook OAuth not configured"` :
→ Les variables d'environnement ne sont pas correctement configurées

### 3. Consulter les Logs
Dashboard Render → Onglet **"Logs"**
- Vérifier le démarrage de l'application
- Chercher des erreurs de configuration

---

## 🚨 Troubleshooting

### Erreur: "Google OAuth not configured"
**Cause** : Variables `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, ou `GOOGLE_REDIRECT_URI` manquantes

**Solution** :
1. Dashboard Render → Environment
2. Vérifier que les 3 variables sont présentes
3. Vérifier qu'il n'y a pas d'espaces superflus
4. Redémarrer le service si nécessaire

### Erreur: "Failed to create user" / utilisateurs perdus après une veille
**Cause historique (NT-071, corrigée)** : avant la migration vers Neon, la base
SQLite vivait sur le disque éphémère de Render et ne survivait pas aux mises en
veille/redéploiements. Le service utilise désormais PostgreSQL Neon
(persistant) — voir [`docs/tech/postgres_neon_migration.md`](postgres_neon_migration.md).
Si ce message réapparaît, vérifier que `DATABASE_URL` pointe bien vers Neon (et
non un fallback SQLite) et consulter les logs de migration au démarrage.

### Le service ne démarre pas : "Database migration failed"
**Cause** : `alembic upgrade head` a échoué au démarrage (`start.py`), avant
Uvicorn — c'est le comportement voulu (NT-071) : un schéma en échec ne sert
jamais de trafic.

**Solution** :
1. Consulter les logs Render (le type d'exception est loggé, jamais l'URL/le mot de passe).
2. Vérifier `DATABASE_MIGRATION_URL` (connexion directe, rôle `neondb_owner`).
3. Vérifier le quota Neon Free (compute/stockage) sur le dashboard Neon.
4. Voir la procédure de rollback dans [`docs/tech/postgres_neon_migration.md`](postgres_neon_migration.md).

### Service en "Sleep Mode"
**Comportement normal** : Après 15min d'inactivité, le service s'endort (tier gratuit)

**Solution** :
- Première requête prend ~30s pour réveiller
- Ou upgrade vers plan payant ($7/mois) pour service toujours actif

---

## 📊 Variables Optionnelles (Futures)

Pour améliorer la production, ajouter plus tard :

| Variable | Valeur Suggérée | Description |
|----------|-----------------|-------------|
| `REDIS_URL` | `redis://...` | Pour state storage OAuth persistant |
| `SENTRY_DSN` | `https://...` | Monitoring erreurs |
| `LOG_LEVEL` | `INFO` | Niveau de logging |
| `ALLOWED_ORIGINS` | `https://app.example.com` | CORS strict |

---

## 🔐 Sécurité

### Bonnes Pratiques

✅ **DO** :
- Marquer toutes les credentials comme **"Secret"** sur Render
- Utiliser des valeurs différentes par environnement (dev/staging/prod)
- Rotater `JWT_SECRET_KEY` régulièrement
- Ne jamais committer les vraies valeurs dans le code

❌ **DON'T** :
- Ne pas partager les credentials dans les issues/PR
- Ne pas utiliser les mêmes credentials dev/prod
- Ne pas exposer les secrets dans les logs

### Rotation des Secrets

Si compromise :
1. Dashboard Render → Environment
2. Modifier la valeur de la variable
3. Save → Service redémarre automatiquement
4. Mettre à jour les credentials côté IdP si nécessaire

---

**Dernière mise à jour** : 17 octobre 2025
