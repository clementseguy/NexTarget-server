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
6. [Intégration dans l'app mobile](#6-intégration-dans-lapp-mobile)
7. [Problèmes courants et solutions](#7-problèmes-courants-et-solutions)
8. [Checklist finale](#8-checklist-finale)

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

```
┌─────────────┐                 ┌─────────────┐                 ┌─────────────┐
│             │                 │             │                 │             │
│  App Mobile │                 │   Serveur   │                 │   Google    │
│             │                 │   Backend   │                 │             │
└──────┬──────┘                 └──────┬──────┘                 └──────┬──────┘
       │                               │                               │
       │ 1. GET /auth/google/start     │                               │
       │──────────────────────────────>│                               │
       │                               │                               │
       │ 2. {auth_url, state}          │                               │
       │<──────────────────────────────│                               │
       │                               │                               │
       │ 3. Ouvre auth_url dans browser│                               │
       │───────────────────────────────────────────────────────────────>│
       │                               │                               │
       │                               │  4. User se connecte + consent│
       │                               │                               │
       │ 5. Redirige vers /callback    │                               │
       │   avec code + state           │                               │
       │<───────────────────────────────────────────────────────────────│
       │                               │                               │
       │ 6. Envoie code au serveur     │                               │
       │──────────────────────────────>│                               │
       │                               │                               │
       │                               │ 7. Échange code contre tokens │
       │                               │──────────────────────────────>│
       │                               │                               │
       │                               │ 8. {id_token, access_token}   │
       │                               │<──────────────────────────────│
       │                               │                               │
       │                               │ 9. Vérifie id_token           │
       │                               │                               │
       │ 10. {access_token: "JWT..."}  │                               │
       │<──────────────────────────────│                               │
       │                               │                               │
```

### 🔑 Les étapes clés expliquées

1. **App demande l'URL d'auth** → Le serveur génère un lien Google
2. **App reçoit l'URL** → Elle contient un `state` pour la sécurité (anti-CSRF)
3. **User clique sur le lien** → Ouvre un navigateur vers Google
4. **User se connecte à Google** → Google demande "autoriser cette app ?"
5. **Google redirige vers notre serveur** → Avec un `code` secret
6. **Serveur échange le code** → Contre les vrais tokens
7. **Serveur vérifie l'identité** → Avec le `id_token` de Google
8. **Serveur crée/récupère l'user** → Dans notre base de données
9. **Serveur génère un JWT** → Notre propre token pour l'app
10. **App reçoit le JWT** → Elle peut maintenant faire des requêtes authentifiées

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

## 6. Intégration dans l'app mobile

### 📱 Flow côté mobile (iOS/Android)

Maintenant qu'on sait que le backend fonctionne, voici comment l'app mobile doit l'utiliser.

#### Étape mobile 1 : Demander l'URL d'auth

```javascript
// Exemple en React Native / Flutter / Swift / Kotlin
const response = await fetch('https://nextarget-server.onrender.com/auth/google/start');
const data = await response.json();

const authUrl = data.auth_url;  // https://accounts.google.com/...
const state = data.state;        // Pour vérifier plus tard
```

#### Étape mobile 2 : Ouvrir l'URL dans un navigateur in-app

```javascript
// React Native avec react-native-inappbrowser
import InAppBrowser from 'react-native-inappbrowser-reborn';

const result = await InAppBrowser.openAuth(
  authUrl,
  'https://nextarget-server.onrender.com/auth/google/callback'
);

// result.url contient l'URL de callback avec le code et state
```

#### Étape mobile 3 : Extraire le code de l'URL de callback

```javascript
// L'URL ressemble à : https://...callback?code=4/xxx&state=yyy

const url = new URL(result.url);
const code = url.searchParams.get('code');
const returnedState = url.searchParams.get('state');

// Vérifier que le state correspond (sécurité)
if (returnedState !== state) {
  throw new Error('Invalid state - possible CSRF attack!');
}
```

#### Étape mobile 4 : Envoyer le code au serveur

```javascript
const tokenResponse = await fetch(
  `https://nextarget-server.onrender.com/auth/google/callback?code=${code}&state=${state}`
);

const tokenData = await tokenResponse.json();
// { access_token: "eyJ...", token_type: "bearer", email: "...", provider: "google" }
```

#### Étape mobile 5 : Stocker le token

```javascript
// Stocke le token en sécurité (Keychain iOS, Keystore Android, SecureStorage)
await SecureStorage.setItem('auth_token', tokenData.access_token);
await SecureStorage.setItem('user_email', tokenData.email);
```

#### Étape mobile 6 : Utiliser le token pour les requêtes

```javascript
const token = await SecureStorage.getItem('auth_token');

const response = await fetch('https://nextarget-server.onrender.com/users/me', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const userData = await response.json();
```

---

### 🎨 UI/UX recommandé

**Écran de login** :

```
┌────────────────────────────┐
│                            │
│     Logo NexTarget         │
│                            │
│   Bienvenue !              │
│   Connecte-toi pour        │
│   commencer                │
│                            │
│  ┌────────────────────┐   │
│  │  🔵 Google Sign In  │   │  ← Bouton avec logo Google
│  └────────────────────┘   │
│                            │
│  En continuant, tu acceptes│
│  nos CGU et Politique de   │
│  confidentialité           │
│                            │
└────────────────────────────┘
```

**États à gérer** :

1. **Initial** : Bouton "Sign in with Google" cliquable
2. **Loading** : Spinner pendant l'ouverture du browser
3. **Authentifié** : Rediriger vers l'écran principal
4. **Erreur** : Afficher un message clair + bouton "Réessayer"

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
