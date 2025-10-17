# Backlog v0.1

Document de pilotage pour la version 0.1. Suivi des objectifs, périmètre, tâches et avancement.

---
## 1. Statuts des tâches
| ID | Objectif                                               | Etat       |
|----|--------------------------------------------------------|------------|
| A1 | Authentifier les utilisateurs de l'app (Google)        | ✅ FAIT    |
| A2 | Authentifier les utilisateurs de l'app (Facebook)      | ✅ FAIT    |
| A3 | Stocker le minimum d'info utilisateur (modèle minimal) | ✅ FAIT    |
| M1 | Servir de middleware Mistral (analyse d'une session)   | ❌ DECALÉ |
| M2 | Orchestration de conseils IA (coach)                   | ❌ DECALÉ |

**Note**: Les tâches M1 et M2 ont été supprimées suite à la décision de créer un backend OAuth-only sans fonctionnalités IA.

---
## 2. Périmètre (In Scope)
### A1. Authentification Google
- Préparation IdP Google (endpoints squelette)
- JWT access token (pas de refresh en v0.1)
- Modèle User: `id, email, provider, hashed_password?, created_at, is_active`
- Unicité composite (`email`, `provider`)

### A2. Authentification Facebook
- Préparation IdP Facebook (endpoints squelette)
- JWT access token (pas de refresh en v0.1)
- Modèle User: `id, email, provider, hashed_password?, created_at, is_active`
- Unicité composite (`email`, `provider`)

### A3. Données utilisateur minimales
- **Aucune info de profil superflue** : seulement email + provider
- **Aucun mot de passe stocké** : authentification 100% déléguée aux IdP
- Champs provider (`google`, `facebook`)
- Pas de stockage persistant des tokens externes

### M1. Middleware Mistral
- Proxifier l'appel : analyse de la session (sans régression)
- Service d’appel unique (logging / latence / erreurs)
- Entrants : informations utilisateur (id) + données de session
- Sortants : analyse (texte)
- Table `ai_interaction` pour historique (prompts + réponses)

### M2. Orchestration coach
- Endpoint `/TO-DEFINE`
- Pipeline simple: normalisation -> prompt engineering -> appel Mistral -> parsing -> scoring trivial
- Sortie: `TO-DEFINE`

---
## 3. Hors Périmètre (Out of Scope v0.1)
- Refresh tokens & rotation
- Multi-factor auth
- Authentification locale (email/password) : **intentionnellement exclu**
- Fonctionnalités IA (Mistral middleware, coaching) : **décalées**
- Conversation multi-tour profonde / contexte long
- Embeddings / vector store
- Personnalisation avancée / profils enrichis
- Quotas dynamiques / facturation

---
## 4. Modèle de Données (v0.1) ✅ IMPLÉMENTÉ

### User (table principale)
```python
class User(SQLModel, table=True):
    id: str                    # UUID v4 auto-généré
    email: str                 # Email fourni par l'IdP OAuth
    provider: str              # 'google' ou 'facebook'
    is_active: bool            # Default True
    created_at: datetime       # UTC timestamp
    
    # Contrainte d'unicité composite
    __table_args__ = (UniqueConstraint("email", "provider"),)
```

**Points clés** :
- Pas de `hashed_password` : aucun mot de passe stocké
- Pas de données personnelles sensibles au-delà de l'email
- Unicité par couple (email, provider) pour supporter multi-IdP

---
## Notes Diverses
- Prévoir passage Pydantic v2 (non prioritaire v0.1)
- ~~Ajouter instrumentation simple (compteur requêtes AI)~~ : N/A (fonctionnalités IA supprimées)

---
## 5. Résumé de la v0.1 (État Final)

### ✅ Implémenté
- Authentification OAuth Google (start + callback avec id_token verification)
- Authentification OAuth Facebook (start + callback avec Graph API)
- JWT access tokens (HS256)
- Modèle User minimal (email + provider uniquement)
- Endpoint `/users/me` (profil utilisateur)
- Health check `/health`
- Documentation OpenAPI complète
- Tests basiques

### 🔒 Sécurité
- **Zero-password backend** : aucun mot de passe stocké
- Authentification 100% déléguée aux IdP externes
- Stockage minimal : email + provider uniquement
- State/nonce pour sécurité OAuth (CSRF protection)

### 📦 Stack Technique
- FastAPI + SQLModel + SQLite
- JWT (PyJWT)
- OAuth 2.0 (google-auth + httpx)
- Tests (pytest + pytest-asyncio)

### 🚀 Déploiement
- Prêt pour VM minimale (1 vCPU / 512MB)
- Configuration via variables d'environnement
- Documentation complète dans README.md

---
Fin du Backlog v0.1 — **Statut : COMPLÉTÉ** (scope réduit, OAuth-only)

