# Vue SERVEUR — projection du backlog unifié

> **Copie de projection.** La **source de vérité** est le backlog unifié, hébergé
> dans le repo **NexTarget-app** : [`docs/backlog/backlog-unifie.md`](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/backlog-unifie.md).
> Ce fichier en est une **projection** (items de portée `server`/`both`). Ne rien
> modifier ici en premier : on met à jour le backlog unifié, puis on recopie.
> Gouvernance : [`docs/backlog/README.md`](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/README.md).

**Repo** : NexTarget-server (FastAPI + SQLModel + SQLite, OAuth + proxy IA)
**Dernière projection** : 2026-07-07 (état du code)

> ⚠️ **Le serveur n'est plus « OAuth-only ».** Il expose aussi le **proxy Coach IA**
> (`/coach/analyze-session`). Les anciens statuts « M1/M2 supprimés/décalés » sont
> **périmés** — voir [journal des incohérences](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/incoherences.md) (I1).

## Items serveur

| ID | Titre | Portée | Prio | Est | Statut | Note serveur |
|---|---|---|---|---|---|---|
| NT-030 | Analyse d'une session par le coach IA | both | Must | M | FAIT | `POST /coach/analyze-session` (`app/api/coach.py`) |
| NT-031 | Prompt d'analyse centralisé | server | Must | S | FAIT | `app/services/prompt_builder.py`, `app/prompts/coach_neutre.yaml` |
| NT-032 | Multi-personas coach (neutre / cool) | both | Should | M | FAIT | `coach_neutre` + `coach_cool` ; sélection app dans Paramètres uniquement |
| NT-033 | Écran "Coach" transverse (endpoint agrégé) | both | Should | L | À FAIRE | nécessitera un endpoint d'analyse multi-sessions |
| NT-034 | Affiner les prompts des personas coach | server | Could | S | À FAIRE | itération contenu `coach_neutre`/`coach_cool` (recette S2) |
| NT-040 | Authentification OAuth Google | both | Must | M | FAIT | `app/api/auth_google.py`, `/auth/token` |
| NT-042 | Profil utilisateur (nom/avatar/niveau) | both | Should | M | FAIT | `app/models/user.py` (champs profil) |
| NT-043 | Endpoint `/users/me` | server | Must | S | FAIT | `app/api/users.py` |
| NT-044 | Authentification OAuth Facebook | both | Could | M | FAIT | `app/api/auth_facebook.py` (côté app : à câbler) |
| NT-045 | Stats publiques / partage de profil | both | Won't-now | M | À FAIRE | — |
| NT-046 | Gamification | both | Won't-now | L | À FAIRE | — |
| NT-047 | Apple Sign In | both | Won't-now | M | À FAIRE | roadmap v0.2 |
| NT-048 | Refresh tokens + rotation | server | Should | M | À FAIRE | roadmap v0.2 |
| NT-053 | Logging structuré + tracing | server | Should | M | À FAIRE | JSON + OpenTelemetry |
| NT-054 | Tests OAuth mockés | server | Should | M | FAIT | `test_oauth_flows.py` : flows complets Google/Facebook mockés |
| NT-055 | CI serveur (tests + couverture) | server | Should | S | FAIT | `.github/workflows/ci.yml` (pytest + cov, Python 3.11) |
| NT-060 | Proxy Mistral (clé hors client) | server | Must | M | FAIT | `app/services/mistral_client.py`, `app/core/config.py` |
| NT-061 | Coach connecté uniquement + rotation clé | both | Must | M | FAIT | code livré (S1) ; rotation clé = action manuelle |
| NT-062 | Rate limiting endpoint coach | server | Must | S | FAIT | `app/services/rate_limiter.py` (10/5min) |
| NT-063 | State OAuth à usage unique (CSRF) | server | Must | S | FAIT | `app/services/oauth_state.py` |
| NT-064 | Vérification du type de token JWT | server | Must | S | FAIT | `app/core/security.py`, `app/api/deps.py` |
| NT-065 | Restreindre CORS par environnement | server | Should | S | FAIT | `CORS_ALLOW_ORIGINS` ; défaut : `*` en dev, aucune origine sinon |
| NT-066 | Vérification du nonce Google | server | Should | S | FAIT | nonce OIDC vérifié dans le callback (400 sinon) |
| NT-070 | Déploiement serveur (Render) | server | Must | S | FAIT | `render.yaml`, `docs/tech/render_setup.md` |
| NT-071 | Migration SQLite → Postgres + Alembic | server | Should | M | À FAIRE | débloque multi-instance (NT-062/063) |
| NT-006 | Analyse d'image de la cible | both | Won't-now | L | À FAIRE | vraisemblablement côté serveur |

## Prochaines actions serveur (hors FAIT), par priorité

- **Must** — (aucun ; la rotation manuelle de la clé Mistral reste à faire côté ops, cf. NT-061).
- **Should** — NT-048, NT-053, NT-071, NT-033.
- **Could** — NT-034 (affinage prompts personas).
- **Won't-now** — NT-045, NT-046, NT-047, NT-006.

## Note de cohérence documentaire

L'`AGENTS.md` de ce repo est **périmé** sur 3 points : « aucune fonctionnalité IA »,
« pas de rate limiting », « User minimal (email + provider) ». Le code contredit les
trois (proxy coach, rate limiter, profil enrichi). À corriger — suivi I3/I6 dans le
[journal des incohérences](https://github.com/clementseguy/NexTarget-app/blob/main/docs/backlog/incoherences.md).
