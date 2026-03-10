
# Feature : affichage des infos d'un utilisateur authentifié et connecté

Voici la conception complète et le plan de développement.

---

## Analyse : données disponibles par source

| Donnée | Google (id_token) | Facebook (Graph /me) | Stockage serveur nécessaire ? |
|---|---|---|---|
| **Nom / pseudo** | `name`, `given_name` | `name` (sans scope supplémentaire) | Oui — initialisé depuis IdP, modifiable par l'user |
| **Photo / avatar** | `picture` (URL) | `picture.data.url` | Oui — URL stockée, rafraîchie à chaque login |
| **Expérience** | ❌ non disponible | ❌ non disponible | Oui — choix utilisateur |
| **Date d'inscription** | ❌ | ❌ | Déjà en base (`created_at`) |

**Ce qui existe déjà dans le code :**
- Google demande le scope `profile` (dans oauth_config.py) → `name` et `picture` sont dans l'id_token reçu, mais **ignorés** au auth_google.py (seuls `email` et `sub` sont extraits)
- Facebook ne demande que `fields=id,email` au auth_facebook.py → `name` et `picture` ne sont pas demandés
- Le modèle User n'a que `id, email, provider, is_active, created_at`

---

## Conception

### Stratégie de stockage (minimum viable)

Conformément à la politique de données minimales :

1. **`display_name`** (Optional[str]) — Initialisé depuis l'IdP au premier login. Rafraîchi à chaque login **sauf si l'utilisateur l'a personnalisé**. Ajoute un flag `display_name_custom: bool = False` pour savoir si c'est la valeur IdP ou un choix user.
2. **`avatar_url`** (Optional[str]) — URL vers la photo IdP. Rafraîchie à chaque login systématiquement (on ne stocke pas l'image, juste l'URL). Aucune donnée binaire.
3. **`experience_level`** (Optional[str]) — Enum `beginner | advanced | expert`. Choix purement utilisateur, null tant que non renseigné.
4. **`created_at`** — Déjà en base ✓

**Total ajouté : 3 colonnes nullables + 1 bool.** Pas de table supplémentaire.

### Modifications du modèle User

```python
class User(SQLModel, table=True):
    # ... champs existants ...
    
    # Profile (from IdP + user choice)
    display_name: Optional[str] = Field(default=None)
    display_name_custom: bool = Field(default=False)  # True if user has manually set their name
    avatar_url: Optional[str] = Field(default=None)    # URL from IdP, refreshed on login
    experience_level: Optional[str] = Field(default=None)  # beginner | advanced | expert
```

### Modifications du flow OAuth

**Google callback** — déjà disponible dans `id_token_claims` :
```python
# Extraire en plus de email/sub :
name = id_token_claims.get("name")
picture = id_token_claims.get("picture")
```

**Facebook callback** — ajouter aux champs demandés :
```python
# Changer "id,email" → "id,email,name,picture.width(200)"
user_params = {
    "fields": "id,email,name,picture.width(200)",
    "access_token": access_token,
}
# Extraire :
name = user_info.get("name")
picture = user_info.get("picture", {}).get("data", {}).get("url")
```

### Modification de `get_or_create_user()`

```python
def get_or_create_user(
    session: Session,
    email: str,
    provider: str,
    display_name: Optional[str] = None,   # NEW
    avatar_url: Optional[str] = None,      # NEW
) -> User:
```

- **Création** : initialise `display_name` et `avatar_url` depuis l'IdP
- **Login existant** : met à jour `avatar_url` systématiquement ; met à jour `display_name` **seulement si** `display_name_custom == False`

### Nouveaux endpoints API

| Méthode | Route | Description |
|---|---|---|
| `GET /users/me` | Existant, **étendu** | Retourne le profil complet (+ `display_name`, `avatar_url`, `experience_level`, `created_at`) |
| `PATCH /users/me/profile` | **Nouveau** | Modifie `display_name` et/ou `experience_level` |

**Schéma de réponse étendu :**
```python
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    provider: str
    display_name: Optional[str]       # NEW
    avatar_url: Optional[str]         # NEW  
    experience_level: Optional[str]   # NEW
    created_at: datetime              # NEW (existait en DB, pas exposé)
```

**Schéma de mise à jour :**
```python
class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    experience_level: Optional[str] = None  # validated against enum

    @validator("experience_level")
    def validate_experience(cls, v):
        if v is not None and v not in ("beginner", "advanced", "expert"):
            raise ValueError("Must be beginner, advanced, or expert")
        return v
```

### Côté mobile (hors scope backend, pour info)

Deux options d'UX mentionnées :
- **Option A — Onglet Paramètres** : page profil intégrée dans les settings. Classique, navigation claire.
- **Option B — Modal/overlay** : s'ouvre depuis un avatar cliquable (header ou sidebar). Plus fluide, ne quitte pas le contexte actuel.

→ **Recommandation** : Option B avec un **bottom sheet ou modal** déclenché par un avatar dans le header. C'est le pattern le plus courant dans les apps mobiles modernes (Instagram, Strava, etc.). Le bottom sheet affiche les infos en lecture, avec un bouton "Modifier" pour basculer en édition.

---

## Plan de développement (tâches backend)

| ID | Tâche | Dépend de | Effort |
|----|-------|-----------|--------|
| P1 | Ajouter les champs au modèle `User` (`display_name`, `display_name_custom`, `avatar_url`, `experience_level`) | — | XS |
| P2 | Mettre à jour `UserPublic` + créer `UserProfileUpdate` dans `schemas/auth.py` | — | XS |
| P3 | Modifier `get_or_create_user()` pour accepter et persister `display_name` / `avatar_url` + logique de refresh | P1 | S |
| P4 | Modifier le callback Google pour extraire `name` et `picture` de l'id_token | P3 | XS |
| P5 | Modifier le callback Facebook pour demander `name,picture` au Graph API et les extraire | P3 | S |
| P6 | Étendre `GET /users/me` (le schéma `UserPublic` étendu suffit) | P1, P2 | XS |
| P7 | Créer `PATCH /users/me/profile` avec validation | P1, P2 | S |
| P8 | Tests : profil étendu dans `/users/me`, mise à jour via PATCH, validation enum, refresh IdP | P6, P7 | M |

**Ordre d'implémentation suggéré** : P1 → P2 → P3 → P4 + P5 (parallélisables) → P6 → P7 → P8

### Points d'attention

- **Migration DB** : SQLite en v0.1, pas d'Alembic. Les nouvelles colonnes `Optional` avec `default=None` sont ajoutées par `create_all()` uniquement sur une DB neuve. Pour une DB existante, il faudra soit la recréer, soit un `ALTER TABLE` manuel. Documenter ce point.
- **Validation `experience_level`** : valider côté serveur (pas seulement côté client). Enum strict : `beginner`, `advanced`, `expert`.
- **Taille de `avatar_url`** : les URLs Google/Facebook peuvent être longues (~200-300 chars). Prévoir une colonne `TEXT` (défaut SQLModel) plutôt qu'un `VARCHAR` court.
- **Sécurité `display_name`** : sanitiser les entrées (longueur max, pas de HTML/scripts) pour éviter du stored XSS côté app mobile.
- **Pas de stockage d'image** : on ne stocke que l'URL de l'IdP. Aucun upload, aucun blob. Conforme à la politique de données minimales.