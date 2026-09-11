# Architecture du serveur

NexTarget-server porte l'authentification sociale, le profil distant et le proxy Coach IA de l'app Flutter. Il sert aussi une landing page publique et une page d'administration en lecture seule.

## Composants

| Couche | Responsabilité |
|---|---|
| `app/api/` | Validation HTTP et orchestration des routes OAuth, tokens, utilisateurs, Coach, exercices et administration |
| `app/core/` | Configuration, JWT, constantes OAuth et logs structurés |
| `app/services/` | Base de données, state OAuth, refresh tokens, prompt, Mistral, rate limiting et auth admin |
| `app/models/` | Tables SQLModel `User`, `RefreshToken` et `CoachCatalogExercise`, contrat commun `Exercise` |
| `app/schemas/` | Contrats Pydantic des utilisateurs, du Coach et d'Exercise |
| `alembic/versions/` | Source de vérité du schéma PostgreSQL de production |

Les couches `core`, `services`, `models` et `schemas` ne dépendent pas des handlers HTTP. Pour Coach, la construction du prompt et l'appel réseau à Mistral sont délégués aux services. Les callbacks OAuth font actuellement exception : les routes Google et Facebook réalisent directement les échanges HTTP avec leur fournisseur.

Le modèle `Exercise` partagé reprend les champs et noms JSON de l'app, dont la
provenance contrôlée `personal` ou `coach_catalog`. La table
`coach_catalog_exercise` accepte uniquement cette seconde provenance et ajoute
le seul état technique `is_active`, vrai par défaut. Elle reste vide tant
qu'aucun contenu validé n'est chargé hors de l'API cliente.

## Routes actives

| Route | Accès | Rôle |
|---|---|---|
| `GET /health` | public | état du processus |
| `GET /auth/google/login` | public | crée state et nonce, renvoie l'URL Google |
| `GET /auth/google/callback` | Google | valide le callback et redirige vers l'app |
| `GET /auth/facebook/start` | public | crée le flow Facebook, non câblé dans l'app |
| `GET /auth/facebook/callback` | Facebook | valide le callback et redirige vers l'app |
| `POST /auth/token/exchange` | callback JWT | émet access token et refresh token |
| `POST /auth/token/refresh` | refresh token | rotation à usage unique de la paire |
| `POST /auth/token/revoke` | refresh token | révoque la famille, réponse 204 idempotente |
| `GET /users/me` | Bearer JWT | profil courant |
| `PATCH /users/me/profile` | Bearer JWT | nom affiché et/ou niveau d'expérience |
| `POST /coach/analyze-session` | Bearer JWT | analyse Mistral d'une session détaillée ; `exerciseId` facultatif identifie son exercice principal et `personal_exercise` transporte son instantané ponctuel |
| `GET /exercises/{exercise_id}` | public | lecture ciblée d'un exercice Coach actif ; aucun parcours ni mutation |
| `GET /app/admin/users` | HTTP Basic | consultation read-only des utilisateurs |
| `GET /` | public | landing page statique |

Le contrat OpenAPI courant est généré par FastAPI sur `/openapi.json` et présenté sur `/docs`. Aucun snapshot YAML n'est maintenu, afin d'éviter une divergence avec les routes.

## Authentification et jetons

Les callbacks OAuth utilisent actuellement deux contrats distincts :

- Google redirige vers `nextarget://callback?token=<callback-jwt>`. Ce JWT expire par défaut après 10 minutes et ne donne pas accès aux API. `POST /auth/token/exchange` vérifie son type et l'utilisateur, puis émet un access token de 60 minutes et un refresh token opaque de 30 jours.
- Facebook redirige vers `nextarget://callback#access_token=<access-jwt>&token_type=bearer&email=...&provider=facebook`. L'access token est utilisable directement sur les API ; ce flux ne passe pas par `/auth/token/exchange` et n'émet pas de refresh token. Il est exposé côté serveur mais n'est pas câblé dans l'app Flutter.

Seul le hash SHA-256 du refresh token est persisté. Chaque refresh tourne le jeton ; rejouer un jeton consommé révoque toute sa famille. La révocation est idempotente et ne révèle pas l'existence du jeton.

Le state OAuth est consommé une seule fois. Pour Google, le `id_token` est vérifié par `google-auth` et son nonce doit correspondre à celui du state.

## Coach IA

Le handler applique la limite par utilisateur, valide la variante de prompt, construit le prompt depuis un template serveur et appelle Mistral avec timeout. Le client n'envoie ni clé ni prompt complet. Les variantes livrées sont `coach_neutre` et `coach_cool`.

Pour un exercice personnel, `session.personal_exercise` est un contrat transitoire
strict : `id` (128 caractères), `name` (120), `origin` fixé à `personal`,
`description` facultative (2 000) et au plus 20 `consignes` de 500 caractères.
`session.exercise_execution` contient uniquement `performed` booléen facultatif,
`protocol_followed` facultatif parmi `yes`, `partially`, `no`, et `comment`
facultatif (1 000 caractères). L'identifiant de l'instantané doit correspondre à
`exerciseId`; une qualification sans instantané personnel est refusée. Les
commentaires de série sont limités à 1 000 caractères, la synthèse à 2 000, la
liste à 100 séries, chaque nombre de coups à l'intervalle 1 à 1 000 et les textes
arme/calibre à 120 caractères.

Tous les champs texte sont sérialisés dans un bloc explicitement désigné comme
données utilisateur non fiables, avec échappement des délimiteurs ; le modèle
reçoit l'ordre de ne suivre aucune instruction qu'ils contiendraient. Pour cet
exercice, le Coach se limite à la session, à `performed`, à
`protocol_followed` et aux commentaires. Une réalisation déclarée fausse est
évaluable ; une réalisation vraie exige un suivi de protocole renseigné ; les
autres cas sont annoncés non évaluables. Aucun critère de réussite métier n'est
exigé. La réponse reçoit déterministiquement la mention « Exercice personnel
hors plan de formation ». Le handler n'utilise aucun service de catalogue et ne
persiste ni session, analyse ou instantané.

Le state OAuth et la limite Coach restent en mémoire et supposent une seule instance. PostgreSQL ne rend pas ces composants multi-instance.

## Données et démarrage

SQLite est le défaut local et autorise `SQLModel.metadata.create_all()`. En production, PostgreSQL est obligatoire et Alembic est l'unique source du schéma. `start.py` exécute les migrations avant Uvicorn et bloque le démarrage si elles échouent.

`DATABASE_URL` sert au runtime avec un rôle sans DDL ; `DATABASE_MIGRATION_URL` sert aux migrations et sauvegardes avec le rôle propriétaire.

## Journalisation et sécurité HTTP

Chaque requête reçoit un `X-Request-ID` et une ligne JSON avec méthode, chemin, statut et durée. Les query strings, tokens, secrets et prompts complets ne sont jamais journalisés.

CORS est ouvert en développement et fermé hors développement sauf configuration explicite. La landing page reçoit une CSP restrictive ; la production ajoute HSTS. L'administration est `no-store`, `noindex`, protégée par HTTP Basic et ne propose aucune mutation.
