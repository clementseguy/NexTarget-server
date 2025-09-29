# Backlog v0.1

Document de pilotage pour la version 0.1. Suivi des objectifs, périmètre, tâches et avancement.

---
## 1. Objectifs (OKR fonctionnels)
| ID | Objectif | Indicateur de succès v0.1 |
|----|----------|---------------------------|
| O1 | Authentifier les utilisateurs de l'app | Un utilisateur peut s'inscrire / se connecter (local) et structure prête pour IdP Google |
| O2 | Stocker le minimum d'info utilisateur | Modèle User minimal sans profil étendu |
| O3 | Servir de middleware Mistral | Endpoints AI passent par un service central + historisation basique |
| O4 | Orchestration de conseils IA (coach) | Endpoint /coach/advice retourne liste structurée de conseils |

---
## 2. Périmètre (In Scope)
### A. Authentification minimale
- Local (email + mot de passe)
- Préparation IdP Google (endpoints squelette)
- JWT access token (pas de refresh en v0.1)
- Modèle User: `id, email, provider, hashed_password?, created_at, is_active`
- Unicité composite (`email`, `provider`)

### B. Données utilisateur minimales
- Aucune info de profil superflue
- Champs provider (`local`, `google`, extensible)
- Pas de stockage persistant des tokens externes

### C. Middleware Mistral
- Service d’appel unique (logging / latence / erreurs)
- Table `ai_interaction` pour historique (prompts + réponses)

### D. Orchestration coach
- Endpoint `/coach/advice`
- Pipeline simple: normalisation -> prompt engineering simple -> appel Mistral -> parsing -> scoring trivial
- Sortie: `[{ advice: str, score: float }]`

---
## 3. Hors Périmètre (Out of Scope v0.1)
- Refresh tokens & rotation
- Multi-factor auth
- Gestion mot de passe oublié / reset
- Conversation multi-tour profonde / contexte long
- Embeddings / vector store
- Personnalisation avancée / profils enrichis
- Quotas dynamiques / facturation

---
## 4. Modèle de Données (v0.1)
### User
| Champ | Type | Notes |
|-------|------|-------|
| id | UUID (str) | PK |
| email | str | Index partiel, unique avec provider |
| provider | enum(str) | local, google, ... |
| hashed_password | str? | Null si provider != local |
| is_active | bool | défaut: true |
| created_at | datetime | auto |

### ai_interaction
| Champ | Type | Notes |
| id | UUID (str) | PK |
| user_id | FK -> user.id | index |
| model | str | ex: mistral-small-latest |
| role | str | user / assistant |
| content | text | prompt ou réponse |
| created_at | datetime | auto |

---
## 5. Epics & Tâches

### EPIC E1 – Auth & User Minimal
- [ ] T1 Affiner modèle User minimal (provider + password optionnel)
- [ ] T2 Ajouter contrainte unicité (email, provider)
- [ ] T3 Adapter register/login pour provider != local
- [ ] T4 Endpoints placeholder Google (`/auth/google/start`, `/auth/google/callback`)

### EPIC E2 – Middleware Mistral
- [ ] T5 Extraire service proxy Mistral (latence + gestion erreurs + structure rate limit)
- [ ] T6 Historiser prompts/réponses (table `ai_interaction`)

### EPIC E3 – Coaching
- [ ] T7 Orchestrateur coaching v1 (pipeline interne)
- [ ] T8 Endpoint `/coach/advice` (retourne conseils scorés)

### EPIC E4 – Qualité & Sécurité
- [ ] T9 Tests auth (local + provider mock)
- [ ] T10 Tests AI / interactions + coach (mock Mistral)
- [ ] T11 Rate limiting simple mémoire (TODO note pour futur Redis)
- [ ] T12 Documentation Backlog & Roadmap (section README)

---
## 6. Critères de DONE v0.1
- Auth locale opérationnelle
- Structure IdP prête (endpoints + validation id_token mockable)
- Modèle User minimal effectif (provider géré)
- Historique interactions AI persisté
- Endpoint `/coach/advice` fonctionnel et testé (mock)
- Tests clés verts (auth + interactions + coach parsing)
- README mis à jour (Roadmap + périmètre)

---
## 7. Risques & Mitigations (Early)
| Risque | Impact | Mitigation initiale |
|--------|--------|---------------------|
| Évolution du schéma User | Rupture future | Faire migration vers Alembic si > v0.1 |
| Latence Mistral variable | Mauvaise UX | Timeout + message côté client |
| Rate limit insuffisant | Abus coût/latence | Placeholder + plan Redis v0.2 |
| Parsing conseils fragile | Résultat incohérent | Format de prompt strict + tests parsing |

---
## 8. Prochaines Étapes Immédiates
1. Implémenter T1/T2 (modèle + unicité) – reset DB dev si nécessaire
2. Créer table `ai_interaction`
3. Ajouter orchestrateur + endpoint coach (structure)
4. Ajouter tests progressifs

---
## 9. Journal d’Avancement (log)
Format: `YYYY-MM-DD – [TID] – action / note`
- (à compléter)

---
## 10. Notes Diverses
- Prévoir passage Pydantic v2 (non prioritaire v0.1)
- Ajouter instrumentation simple (compteur requêtes AI) possible en v0.2

---
Fin du Backlog v0.1

