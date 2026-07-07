# Guide de Test - OAuth2 Mobile Flow avec Google

## Vue d'ensemble

Ce guide vous permet de tester le flow OAuth2 complet pour les applications mobiles avec Google comme Identity Provider.

### Architecture du Flow

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Mobile    │         │   Backend    │         │   Google    │
│     App     │         │  NexTarget   │         │    OAuth    │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │                         │
      │  1. GET /login         │                         │
      │───────────────────────>│                         │
      │                        │                         │
      │  2. {auth_url, state}  │                         │
      │<───────────────────────│                         │
      │                        │                         │
      │  3. Open auth_url      │                         │
      │────────────────────────┼────────────────────────>│
      │                        │                         │
      │  4. User authenticates │                         │
      │<───────────────────────┼─────────────────────────│
      │                        │                         │
      │  5. Redirect to callback with code               │
      │────────────────────────>│                         │
      │                        │  6. Exchange code       │
      │                        │────────────────────────>│
      │                        │                         │
      │                        │  7. id_token            │
      │                        │<────────────────────────│
      │                        │                         │
      │  8. nextarget://callback?token=SHORT_JWT         │
      │<───────────────────────│                         │
      │                        │                         │
      │  9. POST /token/exchange {callback_token}        │
      │───────────────────────>│                         │
      │                        │                         │
      │  10. {access_token}    │                         │
      │<───────────────────────│                         │
      │                        │                         │
```

## Prérequis

### Configuration Google OAuth

1. **Console Google Cloud** : https://console.cloud.google.com/
2. **Créer un projet** ou sélectionner un existant
3. **Activer Google+ API**
4. **Créer des identifiants OAuth 2.0** :
   - Type : Application web
   - URI de redirection autorisé : `https://api.nextarget.app/auth/google/callback`
5. **Récupérer** :
   - Client ID
   - Client Secret

### Variables d'environnement

Créez un fichier `.env` à la racine du projet :

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-in-production

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://api.nextarget.app/auth/google/callback

# Database
DATABASE_URL=sqlite:///./data.db
```

⚠️ **Sécurité** : Ne jamais committer le fichier `.env`

## Démarrage du serveur

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Lancement

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production (via start.py)
python start.py
```

Le serveur démarre sur `http://localhost:8000`

## Tests Manuels

### Test 1 : Health Check

Vérifiez que le serveur fonctionne :

```bash
curl http://localhost:8000/health
```

Réponse attendue :
```json
{"status": "ok"}
```

### Test 2 : Initier le flow OAuth

```bash
curl -X GET "http://localhost:8000/auth/google/login" \
  -H "Accept: application/json"
```

Réponse attendue :
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "random-secure-state-token"
}
```

**Vérifications** :
- ✅ `auth_url` contient le `client_id`
- ✅ `auth_url` contient `redirect_uri=https://api.nextarget.app/auth/google/callback`
- ✅ `state` est un token aléatoire sécurisé

### Test 3 : Simuler le flow complet (Navigateur)

1. **Copier l'URL** retournée dans `auth_url`
2. **Ouvrir dans un navigateur**
3. **Se connecter avec Google**
4. **Observer la redirection** : `nextarget://callback?token=eyJhbGc...`

⚠️ Le navigateur ne pourra pas ouvrir `nextarget://` (custom scheme mobile), mais vous verrez le token dans l'URL.

### Test 4 : Décoder le callback token

Le token retourné est un JWT. Vous pouvez le décoder sur https://jwt.io/ :

**Payload attendu** :
```json
{
  "exp": 1234567890,
  "sub": "user-uuid",
  "type": "callback",
  "provider": "google",
  "email": "user@gmail.com"
}
```

**Vérifications** :
- ✅ `type` est `"callback"`
- ✅ `exp` expire dans 10 minutes
- ✅ `provider` est `"google"`
- ✅ `email` correspond à votre compte Google

### Test 5 : Échanger le callback token

```bash
# Remplacez YOUR_CALLBACK_TOKEN par le token reçu
curl -X POST "http://localhost:8000/auth/token/exchange" \
  -H "Content-Type: application/json" \
  -d '{
    "callback_token": "YOUR_CALLBACK_TOKEN"
  }'
```

Réponse attendue :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "email": "user@gmail.com",
  "provider": "google",
  "user_id": "uuid"
}
```

**Vérifications** :
- ✅ `access_token` est un JWT valide
- ✅ `expires_in` est 3600 (60 minutes)
- ✅ `email` et `provider` sont corrects

### Test 6 : Utiliser l'access token

```bash
# Remplacez YOUR_ACCESS_TOKEN par le token reçu
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Réponse attendue :
```json
{
  "id": "user-uuid",
  "email": "user@gmail.com",
  "is_active": true,
  "provider": "google"
}
```

## Tests Automatisés

### Lancer la suite de tests

```bash
pytest tests/ -v
```

### Tests de sécurité

1. **Token expiré** :
```bash
# Attendre 10 minutes après réception du callback_token
curl -X POST "http://localhost:8000/auth/token/exchange" \
  -H "Content-Type: application/json" \
  -d '{"callback_token": "EXPIRED_TOKEN"}'
```

Réponse attendue :
```json
{
  "detail": "Callback token has expired"
}
```

2. **Token invalide** :
```bash
curl -X POST "http://localhost:8000/auth/token/exchange" \
  -H "Content-Type: application/json" \
  -d '{"callback_token": "invalid.token.here"}'
```

Réponse attendue :
```json
{
  "detail": "Invalid callback token: ..."
}
```

3. **State CSRF invalide** :
```bash
# Tenter d'appeler le callback avec un state inconnu
curl "http://localhost:8000/auth/google/callback?code=test&state=fake-state"
```

Réponse attendue :
```json
{
  "detail": "Invalid or expired state"
}
```

## Tests Mobile (iOS/Android)

### Configuration du Custom Scheme

#### iOS (Info.plist)
```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>nextarget</string>
        </array>
    </dict>
</array>
```

#### Android (AndroidManifest.xml)
```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="nextarget" android:host="callback" />
</intent-filter>
```

### Code exemple (Flutter)

```dart
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';

class AuthService {
  final String apiUrl = 'https://api.nextarget.app';

  Future<void> loginWithGoogle() async {
    // 1. Get auth URL
    final response = await http.get(
      Uri.parse('$apiUrl/auth/google/login'),
    );
    
    final data = json.decode(response.body);
    final authUrl = data['auth_url'];
    
    // 2. Open browser/webview
    if (await canLaunch(authUrl)) {
      await launch(authUrl);
    }
  }

  Future<String?> handleCallback(Uri uri) async {
    // 3. Extract callback token
    final callbackToken = uri.queryParameters['token'];
    
    if (callbackToken == null) return null;
    
    // 4. Exchange for access token
    final response = await http.post(
      Uri.parse('$apiUrl/auth/token/exchange'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'callback_token': callbackToken}),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final accessToken = data['access_token'];
      
      // 5. Store token securely
      await _storeToken(accessToken);
      
      return accessToken;
    }
    
    return null;
  }
  
  Future<void> _storeToken(String token) async {
    // Use flutter_secure_storage or similar
  }
}
```

## Checklist de Validation

### Fonctionnel
- [ ] `/auth/google/login` retourne une URL Google valide
- [ ] Le state token expire après 10 minutes
- [ ] Le callback vérifie et consomme le state (CSRF)
- [ ] Le callback vérifie la signature de l'ID token Google
- [ ] L'utilisateur est créé ou récupéré correctement
- [ ] Le callback token expire après 10 minutes
- [ ] L'exchange retourne un access token de 60 minutes
- [ ] L'access token permet d'accéder à `/users/me`

### Sécurité
- [ ] State token à usage unique (replay protection)
- [ ] Callback token court-vivant (10 min)
- [ ] ID token Google vérifié cryptographiquement
- [ ] JWT secret key suffisamment fort (min 32 caractères)
- [ ] Pas de secret dans les logs
- [ ] HTTPS obligatoire en production

### Architecture
- [ ] Code modulaire et réutilisable
- [ ] Séparation des responsabilités
- [ ] Gestion d'erreur complète
- [ ] Documentation à jour
- [ ] Tests automatisés passants

## Dépannage

### Erreur : "Google OAuth not configured"

**Cause** : Variables d'environnement manquantes

**Solution** :
```bash
# Vérifier les variables
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET
echo $GOOGLE_REDIRECT_URI

# Ou dans Python
python -c "from app.core.config import get_settings; s = get_settings(); print(s.google_client_id)"
```

### Erreur : "Invalid or expired state"

**Cause** : State token expiré (>10 min) ou déjà utilisé

**Solution** : Recommencer le flow depuis `/auth/google/login`

### Erreur : "Token exchange failed"

**Cause** : Mauvaise configuration du `redirect_uri` dans Google Console

**Solution** : Vérifier que `https://api.nextarget.app/auth/google/callback` est dans les URI autorisés

### Erreur : "Callback token has expired"

**Cause** : Délai >10 min entre callback et exchange

**Solution** : L'app mobile doit échanger le token immédiatement

## Performance

### Métriques attendues

- Latence `/auth/google/login` : < 50ms
- Latence `/auth/google/callback` : < 2s (dépend de Google)
- Latence `/auth/token/exchange` : < 100ms
- Latence `/users/me` : < 50ms

### Monitoring

```bash
# Logs en temps réel
tail -f logs/app.log

# Métriques de base
curl http://localhost:8000/health
```

## Prochaines Étapes

1. **Ajouter Facebook OAuth** : Réutiliser `oauth_utils.py`
2. **Ajouter Apple Sign In** : Même pattern
3. **Migrer vers Redis** : Pour `OAuthStateManager` en production multi-instance
4. **Ajouter refresh tokens** : Pour renouveler l'accès sans réauthentification
5. **Implémenter rate limiting** : Protection anti-abuse

## Support

Pour toute question ou problème :
- Documentation API : `/docs` (Swagger UI)
- Repository : https://github.com/clementseguy/NexTarget-server
- Email : contact@nextarget.local
