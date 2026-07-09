# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased] — Sprint S3 (Robustesse serveur)

### 🎉 Ajouté
- NT-055 : pipeline CI GitHub Actions (`.github/workflows/ci.yml`) — pytest +
  couverture (`pytest-cov`) en Python 3.11 sur push/PR.
- NT-054 : tests des flows OAuth complets avec providers mockés
  (`tests/test_oauth_flows.py`) — Google login→callback→exchange→/users/me,
  Facebook start→callback (dont email masqué), branches d'erreur des deux
  providers. Fixtures partagées dans `tests/conftest.py`.
- NT-048 : refresh tokens avec rotation — table `RefreshToken` (hash SHA-256
  seul persisté, famille de rotation), `POST /auth/token/refresh` (usage
  unique, rejeu = révocation de famille), `POST /auth/token/revoke` (logout,
  204 idempotent). `/auth/token/exchange` renvoie en plus `refresh_token` /
  `refresh_expires_in` (champs additifs — clients existants inchangés).
  Config : `REFRESH_TOKEN_EXP_DAYS` (30 j).

- NT-053 : logging structuré — `core/logging.py` (formatter JSON stdlib,
  zéro dépendance) + middleware de corrélation (`X-Request-ID` entrant honoré
  sinon généré, renvoyé en header, présent dans chaque ligne de log) ; une
  ligne `request` par requête (method, path, status, duration_ms — query
  strings jamais loggées). Niveau via `LOG_LEVEL`. Tracing OpenTelemetry
  écarté (single-instance, le request-id suffit).

### 🔄 Modifié
- Tests migrés vers `ASGITransport` (suppression du raccourci httpx `app=`
  déprécié) ; warnings pytest réduits de 30 à 4 (restants = legacy documenté).

## [Unreleased] — Sprint S2 (Demo-ready)

### 🎉 Ajouté
- NT-032 : multi-personas coach — nouvelle variante `coach_cool`
  (`app/prompts/coach_cool.yaml`, ton décontracté/encourageant, mêmes règles
  d'analyse mesurables), enregistrée dans `_VARIANT_FILES`. Sélection côté app
  via `prompt_variant` (contrat d'API inchangé, défaut `coach_neutre`).

## [Unreleased] — Sprint S1 (Sécurité & Qualité)

### 🔒 Sécurité
- NT-065 : CORS restreint par environnement — `Settings.cors_origins` pilote le
  middleware (`*` en dev, aucune origine hors dev, surcharge via
  `CORS_ALLOW_ORIGINS` en liste séparée par des virgules). `.env.example` et
  `render.yaml` documentés. Tests dédiés (`tests/test_cors.py`).
- NT-066 : vérification du nonce OIDC Google dans le callback — le claim
  `nonce` de l'id_token doit égaler le nonce stocké avec le state (400
  `Invalid nonce` sinon, absence = rejet). Premier jeu de tests OAuth avec
  provider mocké (`tests/test_auth_google_nonce.py`), base pour NT-054.

## [0.1.0] - 2025-10-21

### 🎉 Ajouté - OAuth2 Mobile Flow

#### Endpoints
- Nouveau endpoint `POST /auth/token/exchange` pour échanger callback token contre access token
- Nouveau endpoint `GET /auth/google/login` optimisé pour mobile (alias de `/start`)
- Maintien de `GET /auth/google/start` pour rétrocompatibilité

#### Sécurité
- Implémentation de callback tokens courts-vivants (10 minutes) pour OAuth redirect
- Validation stricte du type de token (callback vs access)
- Protection CSRF avec state tokens éphémères
- Protection contre replay attacks (state à usage unique)
- Signature cryptographique des ID tokens Google

#### Architecture
- Fonction `create_callback_token()` pour JWT courts-vivants
- Fonction `verify_callback_token()` pour validation stricte
- Configuration `callback_token_exp_minutes` (défaut: 10)
- Router `auth_token` pour gestion des échanges de tokens
- Code modulaire et réutilisable pour futurs IdPs (Apple, etc.)

#### Documentation
- Guide complet de test : `docs/tech/mobile_oauth_testing_guide.md` (450 lignes)
- Documentation technique : `docs/tech/OAUTH_MOBILE_FLOW.md` (350 lignes)
- Checklist de validation : `docs/tech/VALIDATION_CHECKLIST.md` (200 lignes)
- Résumé d'implémentation : `docs/tech/IMPLEMENTATION_SUMMARY.md`
- Guide de démarrage rapide : `QUICKSTART.md`
- Mise à jour de l'OpenAPI spec : `docs/nextarget-api-v0.1.0.yaml` (+120 lignes)
- README principal mis à jour avec section mobile flow

#### Tests
- Tests unitaires pour création et validation de callback tokens
- Tests de sécurité (tokens invalides, expirés, mauvais type)
- Tests des endpoints `/login`, `/start`, `/token/exchange`
- Total : 7 nouveaux tests (+80 lignes)

### 🔄 Modifié

#### Comportement OAuth Callback
- `/auth/google/callback` redirige maintenant vers `nextarget://callback?token=JWT` au lieu de retourner JSON
- Le token retourné est court-vivant (10 min) et doit être échangé immédiatement
- Flow optimisé pour applications mobiles (iOS/Android)

#### Configuration
- Ajout de `.env.example` avec documentation complète des variables
- Nouvelle variable `CALLBACK_TOKEN_EXP_MINUTES` (défaut: 10)

### 📊 Statistiques

```
Fichiers modifiés    : 7
Fichiers créés       : 6
Lignes de code       : +326
Lignes de doc        : +1200
Tests unitaires      : +7
Taille max fichier   : 150 lignes (< 500 cible)
```

### 🎯 Impact

- ✅ Aucune régression fonctionnelle
- ✅ Rétrocompatibilité totale (alias `/start`)
- ✅ Database schema inchangé
- ✅ Architecture stateless préservée
- ✅ Sécurité renforcée (tokens courts)

### 🔐 Sécurité

- Callback tokens expiration automatique (10 min)
- Access tokens expiration standard (60 min)
- State tokens CSRF protection (10 min)
- Validation stricte des types de tokens
- Signature HS256 avec secret fort requis

### 📚 Documentation Complète

Voir : `docs/tech/implementation_summary.md` pour le résumé exécutif complet.

## [0.0.1] - 2025-10-XX (Version initiale)

### Ajouté
- Authentification OAuth Google
- Authentification OAuth Facebook
- Endpoints `/auth/google/start` et `/auth/google/callback`
- Endpoints `/auth/facebook/start` et `/auth/facebook/callback`
- Endpoint protégé `/users/me`
- JWT access tokens (60 minutes)
- State management pour CSRF protection
- Database SQLite via SQLModel
- Configuration par variables d'environnement
- Documentation OpenAPI/Swagger
- Tests de base

---

## Types de changements

- `Ajouté` : nouvelles fonctionnalités
- `Modifié` : changements de fonctionnalités existantes
- `Déprécié` : fonctionnalités bientôt supprimées
- `Supprimé` : fonctionnalités supprimées
- `Corrigé` : corrections de bugs
- `Sécurité` : vulnérabilités corrigées

## Références

- [Architecture OAuth Mobile](docs/tech/architecture.md)
- [Guide de test](docs/tech/oauth_mobile_testing.md)
- [Guide de démarrage](docs/guides/quickstart.md)
