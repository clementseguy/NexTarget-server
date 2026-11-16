# Administration read-only des utilisateurs — NT-049

Cette interface opérationnelle permet d’observer les utilisateurs inscrits sans
modifier la base. Elle est distincte de l’authentification OAuth des utilisateurs
de l’application mobile.

La page est servie sous `/app/admin` afin de la distinguer explicitement des
routes JSON de l’API REST. Le préfixe `/app` est réservé aux écrans HTML présents
ou futurs ; `/app/admin` est réservé à l’interface d’administration.

## Périmètre

- **Page HTML (hors API REST)** : `GET /app/admin/users`
- **Authentification** : HTTP Basic, à utiliser uniquement via HTTPS
- **Données** : ID interne, email, provider, nom affiché, statut, avatar et date
  de création — uniquement les champs existants du modèle `User`
- **Lecture seule** : aucune route de création, modification ou suppression
  n’existe sous `/app/admin`

La page n’affiche jamais de token, de secret, de mot de passe ou d’empreinte de
mot de passe. Ses réponses portent des directives `no-store` et `noindex`.

## Générer l’empreinte du mot de passe

Le mot de passe brut ne doit être enregistré ni dans `.env`, ni dans Render. À
la racine du dépôt, générer localement une empreinte scrypt salée :

```bash
python3 -c 'from getpass import getpass; from app.services.admin_auth import hash_admin_password; print(hash_admin_password(getpass("Admin password: ")))'
```

La commande ne montre pas la saisie et affiche une valeur commençant par
`scrypt$`. Copier uniquement cette valeur dans le gestionnaire de secrets.

## Configuration locale

Ajouter les deux variables à un fichier `.env` non commité :

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=scrypt$16384$8$1$<salt>$<derived-key>
```

Les deux valeurs sont obligatoires. Si l’une manque, l’administration répond
`503 Administration is not configured` et reste fermée.

Démarrer le serveur puis ouvrir :

```text
http://localhost:8000/app/admin/users
```

HTTP est acceptable uniquement pour une boucle locale de développement. Sur un
réseau ou en production, utiliser exclusivement HTTPS.

## Configuration Render

Dans **Render Dashboard → Environment**, définir comme secrets :

1. `ADMIN_USERNAME` ;
2. `ADMIN_PASSWORD_HASH`, avec l’empreinte générée localement.

Ne jamais définir de variable `ADMIN_PASSWORD` contenant le mot de passe brut.
`render.yaml` déclare les deux valeurs avec `sync: false` : le dépôt ne contient
donc aucune valeur réelle.

Après redéploiement, ouvrir :

```text
https://nextarget-server.onrender.com/app/admin/users
```

Le navigateur demande les credentials HTTP Basic. Pour terminer complètement
une session Basic, fermer toutes les fenêtres du navigateur concerné ; aucun
cookie de session n’est créé par NexTarget.

## Constats sur le login Google

L’audit demandé par NT-049 constate le fonctionnement suivant, sans le modifier :

1. le callback vérifie le `id_token` et exige les claims `email` et `sub` ;
2. le `sub` Google n’est pas stocké dans le modèle utilisateur ;
3. `get_or_create_user()` recherche l’utilisateur par le couple exact
   `(email, provider)` ;
4. une contrainte unique protège ce même couple ;
5. une ligne n’est créée que lorsque cette recherche ne trouve aucun résultat ;
6. l’URL d’autorisation Google contient actuellement `prompt=consent`, ce qui
   force un écran de consentement à chaque nouveau flow OAuth ;
7. la production utilise PostgreSQL via `DATABASE_URL`; l'interface n'utilise
   jamais la connexion propriétaire réservée aux migrations.

La correction éventuelle de l'identité Google ou du consentement est hors
périmètre de NT-049 et doit faire l'objet d'un changement séparé.
