# Quick Start - OAuth2 Mobile Flow

Guide rapide pour tester le flow OAuth2 mobile en 5 minutes.

## Prérequis

```bash
# 1. Vérifier Python
python3 --version  # >= 3.10

# 2. Installer les dépendances
pip install -r requirements.txt
```

## Configuration (2 minutes)

### 1. Créer le fichier `.env`

```bash
cp .env.example .env
```

### 2. Configurer Google OAuth

Visitez https://console.cloud.google.com/apis/credentials

1. Créer un projet
2. Activer Google+ API
3. Créer OAuth 2.0 Client ID (Web application)
4. Ajouter redirect URI : `http://localhost:8000/auth/google/callback`
5. Copier Client ID et Client Secret

### 3. Éditer `.env`

```bash
# Remplacer ces valeurs
JWT_SECRET_KEY=votre-secret-aleatoire-min-32-chars
GOOGLE_CLIENT_ID=votre-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-votre-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

## Lancement (30 secondes)

```bash
# Démarrer le serveur
uvicorn app.main:app --reload --port 8000
```

Serveur prêt sur http://localhost:8000

## Test du Flow (2 minutes)

### 1. Health Check

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

### 2. Obtenir l'URL d'authentification

```bash
curl http://localhost:8000/auth/google/login | jq
```

Vous recevez :
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random-token"
}
```

### 3. Authentification Google

1. Copier `auth_url` et ouvrir dans un navigateur
2. Se connecter avec Google
3. Accepter les permissions
4. Observer la redirection : `nextarget://callback?token=eyJhbGc...`

💡 Le navigateur ne pourra pas ouvrir `nextarget://` mais vous verrez le token dans l'URL.

### 4. Copier le callback token

Depuis l'URL : `nextarget://callback?token=**COPIER_CE_TOKEN**`

### 5. Échanger le token

```bash
curl -X POST http://localhost:8000/auth/token/exchange \
  -H "Content-Type: application/json" \
  -d '{"callback_token": "VOTRE_TOKEN_ICI"}' | jq
```

Vous recevez :
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "email": "votre@email.com",
  "provider": "google",
  "user_id": "uuid"
}
```

### 6. Utiliser l'access token

```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer VOTRE_ACCESS_TOKEN" | jq
```

Vous recevez :
```json
{
  "id": "uuid",
  "email": "votre@email.com",
  "is_active": true,
  "provider": "google"
}
```

✅ **Flow OAuth2 mobile fonctionnel !**

## Débuggage

### Erreur : "Google OAuth not configured"

```bash
# Vérifier les variables d'environnement
cat .env | grep GOOGLE
```

→ S'assurer que `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, et `GOOGLE_REDIRECT_URI` sont définis.

### Erreur : "Invalid or expired state"

→ Recommencer depuis l'étape 2 (le state expire après 10 minutes)

### Erreur : "Callback token has expired"

→ Échanger le token plus rapidement (expire après 10 minutes)

## Documentation complète

- **Guide de test** : `docs/tech/mobile_oauth_testing_guide.md`
- **Documentation technique** : `docs/tech/OAUTH_MOBILE_FLOW.md`
- **Checklist validation** : `docs/tech/VALIDATION_CHECKLIST.md`
- **API Swagger** : http://localhost:8000/docs

## Support

En cas de problème :
1. Vérifier les logs du serveur
2. Consulter la documentation complète
3. Tester avec `pytest tests/test_auth.py -v`

---

**Temps total : ~5 minutes** ⏱️
