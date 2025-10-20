# Guide d'Implémentation : Authentification Google OAuth 2.0

**Public cible** : Développeur junior  
**Temps estimé** : 30-45 minutes  
**Prérequis** : Compte Google, accès au code backend

---

## 📚 Table des Matières

1. [Comprendre OAuth 2.0 (la base)](#1-comprendre-oauth-20-la-base)
2. [Vue d'ensemble du flow](#2-vue-densemble-du-flow)
3. [Configuration Google Cloud Console](#3-configuration-google-cloud-console)
4. [Configuration du serveur](#4-configuration-du-serveur)
5. [Test de l'intégration](#5-test-de-lintégration)
6. [Intégration dans l'app mobile Flutter](#6-intégration-dans-lapp-mobile-flutter)
7. [Problèmes courants et solutions](#7-problèmes-courants-et-solutions)
8. [Checklist finale](#8-checklist-finale)
9. [FAQ technique détaillée](#9-faq-technique-détaillée)

---

## 1. Comprendre OAuth 2.0 (la base)

### 🤔 C'est quoi OAuth 2.0 ?

**Analogie simple** : Imagine que tu veux entrer dans un bâtiment sécurisé (notre app). Au lieu de créer un nouveau badge, tu montres ta carte d'identité Google que le gardien (notre serveur) vérifie auprès de Google. Si Google dit "oui, c'est bien lui", le gardien te donne un badge temporaire (JWT token) pour accéder au bâtiment.

### 🎯 Pourquoi c'est mieux qu'un login/password classique ?

| Login classique | OAuth Google |
|-----------------|--------------|
| ❌ User doit créer un nouveau mot de passe | ✅ Utilise son compte Google existant |
| ❌ On doit stocker les mots de passe (risque) | ✅ On ne stocke PAS les mots de passe |
| ❌ User doit s'en souvenir | ✅ Déjà connecté à Google = 1 clic |
| ❌ Récupération mot de passe = galère | ✅ Géré par Google |

---

## 2. Vue d'ensemble du flow

### 📊 Schéma du flow complet

**⚠️ ATTENTION : Ce schéma montre le flow COMPLET. Voir section 6 pour les détails Flutter.**

```
┌─────────────┐                 ┌─────────────┐                 ┌─────────────┐
│             │                 │             │                 │             │
│  App Mobile │                 │   Serveur   │                 │   Google    │
│   Flutter   │                 │   Backend   │                 │             │
└──────┬──────┘                 └──────┬──────┘                 └──────┬──────┘
       │                               │                               │
       │ 1. GET /auth/google/start     │                               │
       │──────────────────────────────>│                               │
       │                               │                               │
       │ 2. {auth_url, state}          │                               │
       │<──────────────────────────────│                               │
       │                               │                               │
       │ 3. Ouvre auth_url dans        │                               │
       │    flutter_web_auth_2         │                               │
       │───────────────────────────────────────────────────────────────>│
       │                               │                               │
       │                               │  4. User se connecte + consent│
       │                               │                               │
       │ 5. Google redirige vers       │                               │
       │    /callback avec code        │                               │
       │                               │<──────────────────────────────│
       │                               │                               │
       │                               │ 6. Échange code contre tokens │
       │                               │──────────────────────────────>│
       │                               │                               │
       │                               │ 7. {id_token, access_token}   │
       │                               │<──────────────────────────────│
       │                               │                               │
       │                               │ 8. Vérifie id_token + crée user│
       │                               │                               │
       │ 9. flutter_web_auth_2         │                               │
       │    intercepte la réponse      │                               │
       │    JSON du serveur            │                               │
       │<──────────────────────────────│                               │
       │                               │                               │
       │ 10. Parse JSON et stocke JWT  │                               │
       │                               │                               │
```

### 🔑 Les étapes clés expliquées

1. **App demande l'URL d'auth** → Le serveur génère un lien Google
2. **App reçoit l'URL** → Elle contient un `state` pour la sécurité (anti-CSRF)
3. **User clique → navigateur in-app s'ouvre** → Via `flutter_web_auth_2.authenticate()`
4. **User se connecte à Google** → Google demande "autoriser cette app ?"
5. **Google redirige vers `/callback`** → Avec un `code` secret (le serveur reçoit cette requête)
6. **Serveur échange le code** → Contre les vrais tokens auprès de Google
7. **Serveur vérifie l'identité** → Avec le `id_token` de Google
8. **Serveur crée/récupère l'user** → Dans notre base de données
9. **Serveur génère un JWT et le retourne en JSON** → Le navigateur in-app affiche cette réponse
10. **flutter_web_auth_2 intercepte la page** → Parse le JSON et retourne le JWT à l'app Flutter
11. **App stocke le JWT** → Elle peut maintenant faire des requêtes authentifiées

---

## 3. Configuration Google Cloud Console

### 📋 Étape 3.1 : Créer un projet

1. **Va sur** : https://console.cloud.google.com/
2. **Connecte-toi** avec ton compte Google (perso ou pro, peu importe)
3. **En haut à gauche**, clique sur le sélecteur de projet (à côté de "Google Cloud")

   ```
   ┌─────────────────────────────────────┐
   │ ☰  Google Cloud  ▼ [Mon Projet]   │
   │                     └─ Clique ici   │
   └─────────────────────────────────────┘
   ```

4. **Dans la popup**, clique sur **"NEW PROJECT"** (en haut à droite)
5. **Remplis** :
   - **Project name** : `NexTarget` (ou ce que tu veux)
   - **Location** : Laisse "No organization" (sauf si tu as une organisation)
6. **Clique** sur **"CREATE"**
7. **Attends 5-10 secondes** → Une notification apparaît en haut à droite

⚠️ **PIÈGE COURANT** : Si tu ne vois pas la notification, rafraîchis la page et vérifie que ton projet est sélectionné en haut.

---

### 📋 Étape 3.2 : Activer l'API Google+

1. **Menu (☰)** → **"APIs & Services"** → **"Library"**
   
   ```
   ☰ Menu
   ├── APIs & Services
   │   ├── Dashboard
   │   ├── Library          ← Clique ici
   │   ├── Credentials
   │   └── OAuth consent screen
   ```

2. **Barre de recherche** : tape `Google+ API` ou `People API`

3. **Clique sur** "Google+ API" (icône G+ colorée)

4. **Clique sur** le bouton bleu **"ENABLE"**

5. **Attends 3-5 secondes** → La page change et montre "API enabled"

⚠️ **PIÈGE COURANT** : Si tu vois "Manage" au lieu de "Enable", c'est que c'est déjà activé. Parfait !

---

### 📋 Étape 3.3 : Configurer l'écran de consentement OAuth

C'est l'écran que l'user voit quand il se connecte avec Google.

1. **Menu (☰)** → **"APIs & Services"** → **"OAuth consent screen"**

2. **Choisis le type d'user** :
   - Si c'est pour tester : **"External"** (n'importe qui avec un compte Google)
   - Si c'est pour une entreprise avec Google Workspace : "Internal"
   
   👉 **Pour nous : choisis "External"**

3. **Clique** sur **"CREATE"**

4. **Page 1 : App information**

   Remplis les champs suivants :

   | Champ | Valeur à mettre | Pourquoi |
   |-------|-----------------|----------|
   | **App name** | `NexTarget` | Le nom que l'user verra |
   | **User support email** | Ton email | Pour que Google te contacte si problème |
   | **App logo** | (optionnel) | Pour faire joli |
   | **Application home page** | (vide pour l'instant) | On ajoutera plus tard |
   | **Authorized domains** | `onrender.com` | Le domaine de notre serveur |
   | **Developer contact email** | Ton email | Encore pour Google te contacter |

   ⚠️ **ATTENTION** : Pour "Authorized domains", tape juste `onrender.com` (sans `https://` ni `www`)

5. **Clique** sur **"SAVE AND CONTINUE"**

6. **Page 2 : Scopes**
   
   - Les scopes par défaut sont OK (email, profile, openid)
   - **Clique juste** sur **"SAVE AND CONTINUE"** (on ne touche à rien)

7. **Page 3 : Test users**
   
   - Pour l'instant, **skip cette étape**
   - **Clique** sur **"SAVE AND CONTINUE"**

8. **Page 4 : Summary**
   
   - Vérifie que tout est OK
   - **Clique** sur **"BACK TO DASHBOARD"**

✅ **C'est fait !** L'écran de consentement est configuré.

---

### 📋 Étape 3.4 : Créer les credentials OAuth 2.0

C'est ici qu'on obtient le `CLIENT_ID` et `CLIENT_SECRET`.

1. **Menu (☰)** → **"APIs & Services"** → **"Credentials"**

2. **En haut**, clique sur **"+ CREATE CREDENTIALS"**

3. **Choisis** : **"OAuth 2.0 Client ID"**

4. **Si c'est la première fois**, Google te demande de configurer le consent screen → clique sur "CONFIGURE CONSENT SCREEN" et refais l'étape 3.3

5. **Application type** : Choisis **"Web application"**

6. **Name** : `NexTarget Web Client` (ou ce que tu veux)

7. **Authorized JavaScript origins** :
   
   - **Clique** sur **"+ ADD URI"**
   - **Tape** : `https://nextarget-server.onrender.com`
   
   ⚠️ **ATTENTION** : 
   - Il faut le `https://`
   - Remplace `nextarget-server` par le vrai nom de ton service Render
   - Pas de `/` à la fin

8. **Authorized redirect URIs** :
   
   - **Clique** sur **"+ ADD URI"**
   - **Tape** : `https://nextarget-server.onrender.com/auth/google/callback`
   
   ⚠️ **SUPER IMPORTANT** : 
   - Cette URL doit être **EXACTEMENT** celle que ton serveur attend
   - Un espace, une faute de frappe = ça ne marche pas
   - Vérifie 3 fois avant de continuer

9. **Clique** sur **"CREATE"**

10. **Une popup apparaît avec tes credentials** :

    ```
    ┌─────────────────────────────────────────────┐
    │   OAuth client created                      │
    │                                             │
    │   Your Client ID                            │
    │   123456789-abc...apps.googleusercontent.com│
    │   [Copy button]                             │
    │                                             │
    │   Your Client Secret                        │
    │   GOCSPX-xxx_yyy_zzz                       │
    │   [Copy button]                             │
    │                                             │
    │   [Download JSON]  [OK]                     │
    └─────────────────────────────────────────────┘
    ```

11. **⚠️ NE FERME PAS CETTE POPUP TOUT DE SUITE !**

12. **Copie les 2 valeurs** quelque part (Notes, TextEdit, un fichier temporaire)

    ```
    CLIENT_ID=123456789-abc...apps.googleusercontent.com
    CLIENT_SECRET=GOCSPX-xxx_yyy_zzz
    ```

13. **Optionnel mais recommandé** : Clique sur "Download JSON" pour avoir un backup

14. **Clique** sur **"OK"**

✅ **Bravo !** Tu as tes credentials Google. Garde-les en sécurité.

---

## 4. Configuration du serveur

### 📋 Étape 4.1 : Ajouter les variables d'environnement sur Render

Maintenant on va donner ces credentials à notre serveur.

1. **Va sur** : https://dashboard.render.com/

2. **Clique** sur ton service (probablement `nextarget-server` ou `nextarget-api`)

3. **Dans la sidebar à gauche**, clique sur **"Environment"**

4. **Tu vas ajouter 3 variables**. Pour chacune :
   - Clique sur **"Add Environment Variable"**
   - Remplis **Key** et **Value**
   - Clique sur **"Save Changes"** (ou continue à en ajouter)

---

#### Variable 1 : GOOGLE_CLIENT_ID

| Champ | Valeur |
|-------|--------|
| **Key** | `GOOGLE_CLIENT_ID` |
| **Value** | Colle le Client ID copié (ex: `123456789-abc...apps.googleusercontent.com`) |
| **Secret ?** | ❌ Non coché (c'est public, pas grave) |

⚠️ **PIÈGE** : Vérifie qu'il n'y a pas d'espaces avant/après quand tu colles !

---

#### Variable 2 : GOOGLE_CLIENT_SECRET

| Champ | Valeur |
|-------|--------|
| **Key** | `GOOGLE_CLIENT_SECRET` |
| **Value** | Colle le Client Secret (ex: `GOCSPX-xxx_yyy_zzz`) |
| **Secret ?** | ✅ **OUI, coche cette case !** (pour masquer la valeur) |

⚠️ **SUPER IMPORTANT** : Coche bien "Secret" pour cette variable !

---

#### Variable 3 : GOOGLE_REDIRECT_URI

| Champ | Valeur |
|-------|--------|
| **Key** | `GOOGLE_REDIRECT_URI` |
| **Value** | `https://nextarget-server.onrender.com/auth/google/callback` |
| **Secret ?** | ❌ Non coché |

⚠️ **ATTENTION** : Cette URL doit être **EXACTEMENT** la même que celle mise dans Google Cloud Console !

---

5. **Clique** sur **"Save Changes"** (en bas ou en haut de la page)

6. **Le service va redémarrer** → Attends 10-20 secondes

7. **Vérifie que c'est bien redémarré** :
   - Les logs montrent "Your service is live 🎉"
   - Le statut est "Live" en vert

✅ **Configuration serveur terminée !**

---

### 📋 Étape 4.2 : Vérifier que les variables sont bien chargées

1. **Dans Render, onglet "Logs"**

2. **Cherche** une ligne comme :
   ```
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:10000
   ```

3. **Si tu vois ça** → C'est bon, le serveur a démarré

4. **Si tu vois des erreurs** → Regarde la section "Problèmes courants" en bas

---

## 5. Test de l'intégration

### 🧪 Test 1 : Vérifier que le endpoint /start fonctionne

**Objectif** : Vérifier que le serveur génère bien une URL Google.

1. **Ouvre ton terminal** (ou Postman, ou Insomnia)

2. **Lance cette commande** :

   ```bash
   curl https://nextarget-server.onrender.com/auth/google/start
   ```

   ⚠️ Remplace `nextarget-server` par le vrai nom de ton service !

3. **Résultat attendu** :

   ```json
   {
     "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=123...",
     "state": "abc123xyz..."
   }
   ```

4. **Si tu vois ce JSON** → ✅ Parfait ! Passe au test 2

5. **Si tu vois une erreur** → Regarde la section "Problèmes courants"

---

### 🧪 Test 2 : Tester le flow complet manuellement

**Objectif** : Se connecter avec Google et récupérer un JWT.

1. **Copie l'URL** du champ `auth_url` (le lien qui commence par `https://accounts.google.com...`)

2. **Colle-la dans ton navigateur** et appuie sur Entrée

3. **Tu arrives sur la page Google** :
   
   ```
   ┌──────────────────────────────────────┐
   │  Sign in with Google                 │
   │                                      │
   │  [ton-email@gmail.com]              │
   │                                      │
   │  NexTarget wants to:                 │
   │  ✓ View your email address          │
   │  ✓ View your basic profile info     │
   │                                      │
   │  [Cancel]  [Continue]                │
   └──────────────────────────────────────┘
   ```

4. **Clique** sur **"Continue"**

5. **Tu es redirigé** vers une URL comme :
   ```
   https://nextarget-server.onrender.com/auth/google/callback?code=4/xxx&state=yyy
   ```

6. **Le navigateur affiche un JSON** :

   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "email": "ton-email@gmail.com",
     "provider": "google"
   }
   ```

7. **Si tu vois ce JSON** → 🎉 **BRAVO ! Ça marche !**

8. **Copie le `access_token`** (tout le long texte `eyJ...`) → On va le tester

---

### 🧪 Test 3 : Utiliser le JWT pour accéder à /users/me

**Objectif** : Vérifier que le JWT fonctionne pour les requêtes authentifiées.

1. **Dans ton terminal**, lance :

   ```bash
   curl -H "Authorization: Bearer TON_ACCESS_TOKEN_ICI" \
        https://nextarget-server.onrender.com/users/me
   ```

   ⚠️ Remplace `TON_ACCESS_TOKEN_ICI` par le token copié à l'étape précédente !

2. **Résultat attendu** :

   ```json
   {
     "id": "uuid-xxx-yyy",
     "email": "ton-email@gmail.com",
     "provider": "google",
     "is_active": true,
     "created_at": "2025-10-19T..."
   }
   ```

3. **Si tu vois ton email** → ✅ Parfait ! L'authentification fonctionne de bout en bout

---

## 6. Intégration dans l'app mobile Flutter

### 📱 Package Flutter recommandé : flutter_web_auth_2

**🎯 Choix du package** :

| Package | Avantages | Inconvénients | Verdict |
|---------|-----------|---------------|---------|
| **flutter_web_auth_2** | ✅ Léger (50KB)<br>✅ Spécialisé OAuth<br>✅ Intercepte automatiquement la réponse<br>✅ Gère les custom schemes | ❌ Moins de contrôle sur le WebView | ✅ **RECOMMANDÉ** |
| flutter_inappwebview | ✅ Très configurable<br>✅ Accès complet au DOM | ❌ Lourd (500KB+)<br>❌ Overkill pour OAuth simple | ⚠️ Si besoin avancé uniquement |
| webview_flutter | ✅ Officiel Google | ❌ Basique<br>❌ Interception manuelle complexe | ❌ Pas adapté OAuth |

**👉 Pour ce projet : Utilise `flutter_web_auth_2`**

---

### 📦 Installation

1. **Ajoute le package dans `pubspec.yaml`** :

```yaml
dependencies:
  flutter_web_auth_2: ^3.0.0
  http: ^1.1.0
  flutter_secure_storage: ^9.0.0
```

2. **Installe** :

```bash
flutter pub get
```

---

### 🔧 Configuration iOS (important !)

Dans `ios/Runner/Info.plist`, ajoute avant le dernier `</dict>` :

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>myapp</string>
    </array>
  </dict>
</array>
```

⚠️ **Remplace `myapp` par le nom unique de ton app** (ex: `nextarget`)

---

### 🔧 Configuration Android (important !)

Dans `android/app/src/main/AndroidManifest.xml`, dans `<activity>` :

```xml
<activity android:name=".MainActivity" ...>
  <!-- Contenu existant -->
  
  <!-- Ajoute ceci -->
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="myapp" />
  </intent-filter>
</activity>
```

⚠️ **Remplace `myapp` par le même nom que dans iOS**

---

### 💻 Code Flutter complet

#### Étape 1 : Service d'authentification

Crée `lib/services/auth_service.dart` :

```dart
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AuthService {
  static const String _baseUrl = 'https://nextarget-server.onrender.com';
  static const String _callbackScheme = 'myapp'; // ⚠️ Change selon ton app
  
  /// Lance le flow d'authentification Google OAuth
  Future<Map<String, dynamic>> signInWithGoogle() async {
    try {
      // 1. Obtenir l'URL d'authentification Google depuis le serveur
      final startResponse = await http.get(
        Uri.parse('$_baseUrl/auth/google/start'),
      );
      
      if (startResponse.statusCode != 200) {
        throw Exception('Erreur serveur: ${startResponse.statusCode}');
      }
      
      final startData = jsonDecode(startResponse.body);
      final authUrl = startData['auth_url'] as String;
      final state = startData['state'] as String;
      
      print('🔗 URL Google OAuth: $authUrl');
      
      // 2. Ouvrir le navigateur in-app pour l'authentification Google
      // ⚠️ ATTENTION : On donne l'URL du backend, pas un custom scheme !
      final callbackUrl = '$_baseUrl/auth/google/callback';
      
      final resultUrl = await FlutterWebAuth2.authenticate(
        url: authUrl,
        callbackUrlScheme: _callbackScheme,
      );
      
      print('✅ Callback reçu: $resultUrl');
      
      // 3. Le résultat est une URL custom scheme avec les données
      // Format attendu: myapp://callback#access_token=xxx&token_type=bearer&email=...
      final uri = Uri.parse(resultUrl);
      
      // 4. Parser les paramètres (dans le fragment ou query)
      final params = uri.fragment.isNotEmpty 
          ? Uri.splitQueryString(uri.fragment)
          : uri.queryParameters;
      
      final accessToken = params['access_token'];
      final email = params['email'];
      final provider = params['provider'];
      
      if (accessToken == null || email == null) {
        throw Exception('Token ou email manquant dans la réponse');
      }
      
      print('✅ Authentification réussie: $email');
      
      return {
        'access_token': accessToken,
        'email': email,
        'provider': provider ?? 'google',
      };
      
    } catch (e) {
      print('❌ Erreur authentification: $e');
      rethrow;
    }
  }
  
  /// Récupère les infos de l'utilisateur authentifié
  Future<Map<String, dynamic>> getUserInfo(String token) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/users/me'),
      headers: {'Authorization': 'Bearer $token'},
    );
    
    if (response.statusCode != 200) {
      throw Exception('Erreur lors de la récupération du profil');
    }
    
    return jsonDecode(response.body);
  }
}
```

**⚠️ POINT CRITIQUE : Comment flutter_web_auth_2 intercepte la réponse**

Le backend retourne actuellement du JSON directement :
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "email": "user@gmail.com",
  "provider": "google"
}
```

**Problème** : `flutter_web_auth_2` attend une redirection vers `myapp://callback`, pas du JSON brut.

**Solution** : On doit modifier le backend pour rediriger au lieu de retourner du JSON.

---

### 🔨 Modification requise du backend

#### Option A : Redirection avec fragment (RECOMMANDÉ)

Modifie `app/api/auth_google.py`, fonction `google_auth_callback` :

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

@router.get("/callback")
async def google_auth_callback(
    code: str,
    state: str,
    session: Session = Depends(get_session)
) -> RedirectResponse:  # ⬅️ Change le type de retour
    # ... tout le code existant jusqu'à la génération du token ...
    
    user = get_or_create_user(session, email, provider="google")
    token_response = generate_token_response(user)
    
    # ⚠️ NOUVEAU : Au lieu de retourner du JSON, on redirige
    from urllib.parse import urlencode
    
    # Construit l'URL de redirection avec les données dans le fragment (#)
    callback_url = "myapp://callback"  # ⚠️ Change "myapp" selon ton app
    
    # Utilise le fragment (#) au lieu de query params (?) pour plus de sécurité
    fragment = urlencode({
        'access_token': token_response['access_token'],
        'token_type': token_response['token_type'],
        'email': token_response['email'],
        'provider': token_response['provider'],
    })
    
    redirect_url = f"{callback_url}#{fragment}"
    
    print(f"🔄 Redirection vers: {redirect_url}")
    
    return RedirectResponse(url=redirect_url, status_code=302)
```

**Pourquoi le fragment (#) au lieu de query params (?)** :

- Le fragment n'est JAMAIS envoyé au serveur (plus sécurisé)
- Le token JWT reste uniquement côté client
- Évite les logs serveur avec des tokens

---

#### Option B : Page HTML intermédiaire (si Option A ne marche pas)

Si la redirection directe échoue, utilise une page HTML qui redirige avec JavaScript :

```python
from fastapi.responses import HTMLResponse

@router.get("/callback")
async def google_auth_callback(...) -> HTMLResponse:
    # ... code existant ...
    
    token_response = generate_token_response(user)
    
    # Page HTML qui redirige automatiquement
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentification réussie</title>
    </head>
    <body>
        <h1>✅ Authentification réussie</h1>
        <p>Redirection vers l'application...</p>
        <script>
            // Redirige vers le custom scheme avec le token
            const params = new URLSearchParams({{
                access_token: '{token_response["access_token"]}',
                email: '{token_response["email"]}',
                provider: '{token_response["provider"]}'
            }});
            
            window.location.href = 'myapp://callback#' + params.toString();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
```

---

### 📱 Utilisation dans l'UI Flutter

Crée `lib/screens/login_screen.dart` :

```dart
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _authService = AuthService();
  final _storage = FlutterSecureStorage();
  bool _isLoading = false;
  String? _errorMessage;
  
  Future<void> _signInWithGoogle() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      // 1. Authentification Google OAuth
      final authData = await _authService.signInWithGoogle();
      
      // 2. Stocker le token en sécurité
      await _storage.write(
        key: 'auth_token',
        value: authData['access_token'],
      );
      await _storage.write(
        key: 'user_email',
        value: authData['email'],
      );
      
      // 3. Rediriger vers l'écran principal
      if (mounted) {
        Navigator.pushReplacementNamed(context, '/home');
      }
      
    } catch (e) {
      setState(() {
        _errorMessage = _getErrorMessage(e);
        _isLoading = false;
      });
    }
  }
  
  String _getErrorMessage(dynamic error) {
    final errorStr = error.toString().toLowerCase();
    
    if (errorStr.contains('user_cancelled') || errorStr.contains('canceled')) {
      return 'Connexion annulée';
    } else if (errorStr.contains('network')) {
      return 'Problème de connexion internet';
    } else if (errorStr.contains('timeout')) {
      return 'La requête a expiré, réessaie';
    } else {
      return 'Une erreur est survenue : ${error.toString()}';
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Logo
              Icon(Icons.rocket_launch, size: 80, color: Colors.blue),
              SizedBox(height: 24),
              
              // Titre
              Text(
                'Bienvenue sur NexTarget',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 8),
              Text(
                'Connecte-toi pour commencer',
                style: TextStyle(fontSize: 16, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 48),
              
              // Bouton Google Sign In
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : _signInWithGoogle,
                  icon: _isLoading
                      ? SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(Icons.login),
                  label: Text(
                    _isLoading ? 'Connexion...' : 'Se connecter avec Google',
                    style: TextStyle(fontSize: 16),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
              
              // Message d'erreur
              if (_errorMessage != null) ...[
                SizedBox(height: 16),
                Container(
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: Colors.red),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(color: Colors.red.shade900),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              
              SizedBox(height: 24),
              
              // CGU
              Text(
                'En continuant, tu acceptes nos CGU et notre Politique de confidentialité',
                style: TextStyle(fontSize: 12, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

### 🔒 Utiliser le token pour les requêtes authentifiées

Crée `lib/services/api_service.dart` :

```dart
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';

class ApiService {
  static const String _baseUrl = 'https://nextarget-server.onrender.com';
  final _storage = FlutterSecureStorage();
  
  /// Récupère le token stocké
  Future<String?> _getToken() async {
    return await _storage.read(key: 'auth_token');
  }
  
  /// Requête GET authentifiée
  Future<http.Response> authenticatedGet(String endpoint) async {
    final token = await _getToken();
    
    if (token == null) {
      throw Exception('Non authentifié');
    }
    
    return await http.get(
      Uri.parse('$_baseUrl$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
  }
  
  /// Exemple : récupérer le profil utilisateur
  Future<Map<String, dynamic>> getMyProfile() async {
    final response = await authenticatedGet('/users/me');
    
    if (response.statusCode == 401) {
      throw Exception('Session expirée, reconnecte-toi');
    }
    
    if (response.statusCode != 200) {
      throw Exception('Erreur serveur: ${response.statusCode}');
    }
    
    return jsonDecode(response.body);
  }
}
```

---

### 🎬 Flow complet résumé

1. **User clique sur "Se connecter avec Google"**
2. **App appelle `/auth/google/start`** → Reçoit `auth_url`
3. **flutter_web_auth_2 ouvre `auth_url`** → Navigateur in-app vers Google
4. **User se connecte et accepte** → Google redirige vers `/auth/google/callback?code=XXX`
5. **Serveur traite le callback** :
   - Échange le code contre des tokens auprès de Google
   - Vérifie l'identité de l'user
   - Crée/récupère l'user en base
   - **Redirige vers `myapp://callback#access_token=JWT...`**
6. **flutter_web_auth_2 intercepte** le custom scheme `myapp://`
7. **App parse le fragment** → Extrait `access_token`, `email`, `provider`
8. **App stocke le token** dans FlutterSecureStorage
9. **App redirige** vers l'écran principal

---

### ⚠️ Points d'attention spécifiques Flutter

#### 1. **Custom scheme doit être unique**

- ❌ `myapp://` → Trop générique, conflits possibles
- ✅ `nextarget://` → Unique à ton app
- ✅ `com.yourcompany.nextarget://` → Encore mieux (style reverse domain)

#### 2. **Tester sur un vrai device**

L'authentification OAuth ne fonctionne PAS correctement sur simulateur iOS. Pourquoi ?

- Le simulateur partage les cookies avec Safari de ton Mac
- Peut causer des problèmes de session

**Solution** : Teste toujours sur un vrai iPhone/Android.

#### 3. **Gérer l'annulation user**

Si l'user appuie sur "Annuler" dans le navigateur Google :

```dart
try {
  final result = await FlutterWebAuth2.authenticate(...);
} on PlatformException catch (e) {
  if (e.code == 'CANCELED') {
    print('User a annulé la connexion');
    // N'affiche pas d'erreur, c'est normal
  } else {
    print('Erreur: ${e.message}');
  }
}
```

---

## 7. Problèmes courants et solutions

### ❌ Erreur : "Google OAuth not configured"

**Message exact** :
```json
{
  "detail": "Google OAuth not configured"
}
```

**Causes possibles** :

1. Les variables d'environnement ne sont pas définies sur Render
2. Le service n'a pas redémarré après l'ajout des variables
3. Les noms des variables sont mal orthographiés

**Solution** :

```bash
# 1. Vérifie les variables sur Render Dashboard → Environment
# Elles doivent être EXACTEMENT :
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET
# - GOOGLE_REDIRECT_URI

# 2. Si elles sont bien là, redémarre manuellement :
# Dashboard → Manual Deploy → Deploy latest commit
```

---

### ❌ Erreur : "Invalid or expired state"

**Message exact** :
```json
{
  "detail": "Invalid or expired state"
}
```

**Causes possibles** :

1. Le `state` dans l'URL de callback ne correspond pas à celui généré
2. Le state a expiré (>10 minutes entre /start et /callback)
3. Tu as rafraîchi la page du callback (state déjà consommé)

**Solution** :

```bash
# Recommence le flow depuis le début :
# 1. Appelle /auth/google/start pour avoir un nouveau state
# 2. Utilise l'auth_url immédiatement (< 10 min)
# 3. Ne rafraîchis pas la page de callback
```

---

### ❌ Erreur : "redirect_uri_mismatch"

**Message Google** :
```
Error 400: redirect_uri_mismatch
The redirect URI in the request: https://xxx/callback
does not match the ones authorized for the OAuth client.
```

**Causes** :

1. L'URL dans Google Cloud Console ≠ celle sur Render
2. Faute de frappe dans l'une des deux
3. Slash `/` à la fin (ou pas) qui diffère

**Solution** :

```bash
# 1. Sur Google Cloud Console → Credentials → Ton Client ID → Edit
# Vérifie que l'URL est EXACTEMENT :
https://nextarget-server.onrender.com/auth/google/callback

# 2. Sur Render → Environment → GOOGLE_REDIRECT_URI
# Vérifie que c'est EXACTEMENT la même :
https://nextarget-server.onrender.com/auth/google/callback

# Les 2 doivent être IDENTIQUES (majuscules, /, https, tout)
```

---

### ❌ Erreur : "Token exchange failed: 400"

**Message serveur** :
```json
{
  "detail": "Token exchange failed: {error: invalid_grant}"
}
```

**Causes** :

1. Le `code` d'autorisation a déjà été utilisé (one-time use)
2. Le `code` a expiré (>10 minutes)
3. Le CLIENT_SECRET est incorrect

**Solution** :

```bash
# 1. Recommence le flow depuis /start (nouveau code)
# 2. Vérifie que CLIENT_SECRET sur Render est correct
# 3. Ne réutilise jamais un code d'autorisation
```

---

### ❌ Erreur : "Invalid id_token"

**Message serveur** :
```json
{
  "detail": "Invalid id_token: Token expired"
}
```

**Causes** :

1. L'horloge du serveur est désynchronisée
2. Le id_token est vraiment expiré (rare si flow rapide)

**Solution** :

```bash
# Normalement ne devrait pas arriver en prod.
# Si ça arrive :
# 1. Vérifie l'heure du serveur Render
# 2. Recommence le flow rapidement
# 3. Contacte le lead dev si ça persiste
```

---

### ❌ Le callback ne reçoit rien (page blanche)

**Symptômes** :

- Le navigateur se redirige vers `/callback`
- Mais affiche une page blanche ou "Cannot GET /callback"

**Causes** :

1. Le serveur ne répond pas (crashed)
2. L'URL de callback est mal formée

**Solution** :

```bash
# 1. Vérifie que le serveur est "Live" sur Render Dashboard
# 2. Teste manuellement :
curl https://nextarget-server.onrender.com/health
# Si ça répond {"status": "ok"} → serveur OK

# 3. Vérifie les logs Render pour voir s'il y a eu une erreur
```

---

### ⚠️ Warning : "urllib3 v2 only supports OpenSSL"

**Message dans les logs** :
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+...
```

**C'est grave ?** → ❌ Non, c'est juste un warning. Ça fonctionne quand même.

**Pourquoi ?** → Version de SSL sur le serveur. Pas critique.

**Solution** : Tu peux ignorer ce warning en toute sécurité.

---

## 8. Checklist finale

Avant de dire "c'est bon, c'est terminé", vérifie cette checklist :

### ✅ Configuration Google Cloud

- [ ] Projet Google Cloud créé
- [ ] Google+ API activée
- [ ] OAuth consent screen configuré
- [ ] OAuth 2.0 Client ID créé
- [ ] Redirect URI correctement configuré (avec `/auth/google/callback`)
- [ ] CLIENT_ID et CLIENT_SECRET copiés

### ✅ Configuration Render

- [ ] Variable `GOOGLE_CLIENT_ID` ajoutée
- [ ] Variable `GOOGLE_CLIENT_SECRET` ajoutée (et marquée Secret)
- [ ] Variable `GOOGLE_REDIRECT_URI` ajoutée
- [ ] Service redémarré après ajout des variables
- [ ] Service en statut "Live" (vert)

### ✅ Tests backend

- [ ] `GET /health` répond `{"status": "ok"}`
- [ ] `GET /auth/google/start` retourne `{auth_url, state}`
- [ ] Flow manuel complet fonctionne (browser → callback → JWT)
- [ ] JWT obtenu fonctionne sur `/users/me`
- [ ] L'email Google est bien dans la réponse

### ✅ Documentation mobile

- [ ] Code d'exemple fourni au dev mobile
- [ ] URL du serveur communiquée
- [ ] Explications sur le flow OAuth données
- [ ] Gestion d'erreur expliquée

---

## 📚 Ressources supplémentaires

### 📖 Documentation officielle

- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI OAuth](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Render Environment Variables](https://render.com/docs/environment-variables)

### 🆘 Où demander de l'aide

1. **Slack du projet** : Channel #backend ou #help
2. **Ton lead dev** : Ping-le si tu bloques >30min
3. **Documentation du code** : `app/api/auth_google.py` a des docstrings complètes

---

## 🎓 Concepts avancés (optionnel, pour plus tard)

### 🔐 Qu'est-ce qu'un id_token ?

Le `id_token` est un **JWT** (JSON Web Token) signé par Google qui contient :

```json
{
  "iss": "https://accounts.google.com",
  "sub": "123456789",                    // User ID Google
  "email": "user@gmail.com",
  "email_verified": true,
  "name": "John Doe",
  "picture": "https://...",
  "iat": 1729000000,                     // Issued at (timestamp)
  "exp": 1729003600                      // Expires (1h après)
}
```

**Pourquoi c'est sûr ?** → Le serveur vérifie la signature avec la clé publique de Google. Si quelqu'un modifie le contenu, la signature ne correspond plus.

### 🛡️ Qu'est-ce que le state (CSRF protection) ?

Le `state` protège contre les attaques **CSRF** (Cross-Site Request Forgery).

**Sans state** :
1. Attaquant créé un lien piégé : `https://notre-app/callback?code=CODE_VOLE`
2. Victime clique → Son navigateur envoie ses cookies → On créé une session avec le compte de l'attaquant
3. Victime se retrouve connectée au compte de l'attaquant

**Avec state** :
1. Notre serveur génère un `state` aléatoire et le stocke
2. Google redirige avec le même `state`
3. On vérifie que le `state` reçu = celui qu'on a généré
4. Si différent → on refuse (attaque détectée)

### 🔄 Refresh tokens (pour plus tard)

Le `access_token` qu'on retourne expire après 60 minutes. Pour éviter que l'user se reconnecte toutes les heures, on pourrait :

1. Stocker le `refresh_token` de Google (on le reçoit dans la réponse)
2. Quand notre JWT expire, l'app mobile appelle `/auth/refresh`
3. Le serveur utilise le refresh_token pour demander un nouveau access_token à Google
4. On renvoie un nouveau JWT à l'app

**Implémentation** : Pas dans la v0.1, mais à prévoir pour la v0.2 !

---

## 9. FAQ technique détaillée

### ❓ Question 1 : Quel package Flutter dois-je utiliser ?

**Question exacte du dev** : _"Le doc mentionne react-native-inappbrowser mais on est sur Flutter. Quel package utiliser ?"_

**Réponse** :

✅ **Utilise `flutter_web_auth_2`** (version 3.0+)

**Comparaison détaillée** :

| Critère | flutter_web_auth_2 | flutter_inappwebview | webview_flutter |
|---------|-------------------|----------------------|-----------------|
| **Taille** | ~50KB | ~500KB+ | ~200KB |
| **Spécialisé OAuth** | ✅ Oui | ❌ Non (usage général) | ❌ Non |
| **Auto-intercept callback** | ✅ Oui | ⚠️ Manuel | ⚠️ Manuel |
| **Custom URL schemes** | ✅ Géré auto | ⚠️ Config complexe | ⚠️ Config complexe |
| **Maintenance** | ✅ Actif | ✅ Actif | ✅ Actif (Google) |
| **Difficulté** | ⭐ Facile | ⭐⭐⭐ Avancé | ⭐⭐ Moyen |

**Verdict final** : `flutter_web_auth_2` est fait EXACTEMENT pour ce use case (OAuth).

**Installation** :
```yaml
dependencies:
  flutter_web_auth_2: ^3.0.0
```

---

### ❓ Question 2 : Comment l'app intercepte le callback du serveur ?

**Question exacte du dev** : _"Comment l'app intercepte https://nextarget-server.onrender.com/auth/google/callback?code=XXX ? Le navigateur affiche le JSON du serveur ?"_

**Réponse détaillée** :

**🔴 Problème actuel** : Le backend retourne du JSON directement :

```json
{
  "access_token": "eyJ...",
  "email": "user@gmail.com",
  "provider": "google"
}
```

**❌ Ce qui se passe** : Le navigateur in-app affiche cette page JSON → L'app ne peut pas l'intercepter facilement.

**✅ Solution : Le backend DOIT rediriger vers un custom scheme**

#### Modification requise du backend

**Dans `app/api/auth_google.py`**, remplace le return final par une redirection :

```python
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

@router.get("/callback")
async def google_auth_callback(
    code: str,
    state: str,
    session: Session = Depends(get_session)
) -> RedirectResponse:  # ⬅️ Change ici
    # ... tout le code existant ...
    
    user = get_or_create_user(session, email, provider="google")
    token_response = generate_token_response(user)
    
    # ⚠️ NOUVEAU : Redirige vers le custom scheme de l'app
    callback_scheme = "nextarget://callback"  # Défini dans l'app Flutter
    
    # Utilise le FRAGMENT (#) pour plus de sécurité
    fragment = urlencode({
        'access_token': token_response['access_token'],
        'token_type': token_response['token_type'],
        'email': token_response['email'],
        'provider': token_response['provider'],
    })
    
    redirect_url = f"{callback_scheme}#{fragment}"
    # Exemple: nextarget://callback#access_token=eyJ...&email=user@gmail.com
    
    return RedirectResponse(url=redirect_url, status_code=302)
```

**Pourquoi `#fragment` au lieu de `?query`** :

- ✅ Le fragment (#) n'est JAMAIS envoyé au serveur (plus sécurisé)
- ✅ Le JWT reste uniquement côté client
- ✅ Évite les logs serveur avec des tokens sensibles

#### Côté Flutter

```dart
final resultUrl = await FlutterWebAuth2.authenticate(
  url: authUrl,
  callbackUrlScheme: 'nextarget',  // Juste le scheme, sans ://
);

// resultUrl = "nextarget://callback#access_token=eyJ...&email=..."
print('✅ URL interceptée: $resultUrl');

final uri = Uri.parse(resultUrl);
final params = Uri.splitQueryString(uri.fragment);  // Parse le fragment

final token = params['access_token'];  // Extrait le JWT
final email = params['email'];
```

**Résumé du flow** :

1. Google redirige → `https://backend/callback?code=XXX`
2. Backend traite le code → Génère le JWT
3. Backend redirige → `nextarget://callback#access_token=JWT`
4. OS intercepte le custom scheme → Ouvre l'app Flutter
5. flutter_web_auth_2 récupère l'URL → Retourne `resultUrl`
6. App parse `resultUrl` → Extrait le token

---

### ❓ Question 3 : Pourquoi RE-appeler /callback ? Le backend ne l'a pas déjà traité ?

**Question exacte du dev** : _"Pourquoi l'étape 4 du guide dit 'Envoyer le code au serveur' alors que Google a déjà redirigé vers /callback ?"_

**Réponse : C'était une ERREUR dans le guide initial** ❌

Il y a **DEUX flows possibles** pour OAuth :

#### Flow A : Backend intermédiaire (NOTRE IMPLÉMENTATION)

```
User → Google → Backend → App
```

**Étapes** :
1. App appelle `/auth/google/start` → Obtient `auth_url`
2. App ouvre `auth_url` dans navigateur in-app
3. User se connecte à Google
4. **Google redirige vers le BACKEND** (`/callback?code=XXX`)
5. **Backend échange le code** contre les tokens auprès de Google
6. **Backend génère le JWT** et redirige vers `myapp://callback#token=JWT`
7. **App intercepte le custom scheme** et récupère le JWT

**Avantages** :
- ✅ Le `CLIENT_SECRET` reste sur le serveur (sécurisé)
- ✅ Logique métier centralisée (création user, etc.)
- ✅ L'app reçoit directement un JWT prêt à l'emploi

**Inconvénient** :
- ⚠️ Nécessite un backend fonctionnel

---

#### Flow B : Mobile direct (Alternative, NON utilisée ici)

```
User → Google → App (l'app échange le code)
```

**Étapes** :
1. App appelle `/auth/google/start` → Obtient `auth_url`
2. App ouvre `auth_url` avec custom scheme dans redirect_uri
3. User se connecte
4. **Google redirige DIRECTEMENT vers `myapp://callback?code=XXX`**
5. **App intercepte** le custom scheme
6. **App envoie le code au backend** via un endpoint dédié
7. **Backend échange le code** et retourne le JWT

**Configuration Google différente** :
```
Redirect URI: myapp://callback  (au lieu de https://backend/callback)
```

**Avantages** :
- ✅ Moins de round-trips réseau

**Inconvénients** :
- ❌ Plus complexe côté mobile
- ❌ Nécessite d'envoyer le code au backend quand même
- ❌ Moins standard

---

### 📊 Comparaison des 3 hypothèses du dev

Le dev avait proposé 3 hypothèses. Voici laquelle on utilise :

| Hypothèse | Description | Utilisée ? |
|-----------|-------------|------------|
| **A** | Google → Backend → Backend retourne JSON → App parse HTML | ❌ Non (mais c'était l'implémentation actuelle INCORRECTE) |
| **B** | Google → Backend → **Backend redirige vers `myapp://callback?token=JWT`** | ✅ **OUI, c'est la bonne** |
| **C** | Google → `myapp://callback?code=XXX` → App appelle backend avec le code | ❌ Non (flow alternatif, plus complexe) |

**Conclusion** : On utilise l'hypothèse B avec une redirection backend.

---

### 🔧 Actions à faire côté backend

Pour que l'hypothèse B fonctionne, **modifie `app/api/auth_google.py`** :

```python
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

@router.get("/callback")
async def google_auth_callback(
    code: str,
    state: str,
    session: Session = Depends(get_session)
) -> RedirectResponse:  # ⬅️ Change le type de retour
    
    # [... tout le code existant jusqu'à la génération du token ...]
    
    user = get_or_create_user(session, email, provider="google")
    token_response = generate_token_response(user)
    
    # ⚠️ REMPLACE le return actuel par ceci :
    callback_url = "nextarget://callback"
    fragment = urlencode(token_response)
    
    return RedirectResponse(
        url=f"{callback_url}#{fragment}",
        status_code=302
    )
```

**Même chose pour Facebook** dans `app/api/auth_facebook.py`.

---

### 🎯 Récapitulatif des custom schemes

**Configuration nécessaire** :

1. **iOS** (`ios/Runner/Info.plist`) :
```xml
<key>CFBundleURLSchemes</key>
<array>
  <string>nextarget</string>  <!-- Sans :// -->
</array>
```

2. **Android** (`android/app/src/main/AndroidManifest.xml`) :
```xml
<data android:scheme="nextarget" />
```

3. **Flutter** (`lib/services/auth_service.dart`) :
```dart
callbackUrlScheme: 'nextarget',  // Sans ://
```

4. **Backend** (`app/api/auth_google.py`) :
```python
callback_url = "nextarget://callback"  # Avec ://
```

**⚠️ IMPORTANT** : Le nom du scheme (`nextarget`) doit être :
- Unique (pas `myapp`, trop générique)
- Le même partout (iOS, Android, Flutter, Backend)
- En minuscules sans espaces

---

## ✨ Conclusion

Si tu as suivi toutes les étapes et que la checklist est complète, **félicitations !** 🎉

Tu as implémenté :
- ✅ OAuth 2.0 avec Google
- ✅ Sécurité CSRF avec state
- ✅ Vérification des id_tokens
- ✅ Génération de JWT pour l'app
- ✅ Tests de bout en bout

**Prochaines étapes** :
1. Demande au dev mobile de tester l'intégration
2. Teste avec plusieurs comptes Google (dont un sans photo de profil)
3. Teste sur un vrai device mobile (pas juste émulateur)

**En cas de problème** :
1. Relis la section "Problèmes courants"
2. Vérifie les logs Render
3. Demande de l'aide sur Slack après avoir tenté de débugger toi-même

**Bonne chance !** 🚀

---

**Dernière mise à jour** : 19 octobre 2025  
**Version du serveur** : NexTarget v0.1  
**Auteur** : [Ton nom / Backend Team]
