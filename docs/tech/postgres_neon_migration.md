# Migration SQLite → PostgreSQL Neon + Alembic (NT-071)

Procédure de référence pour la bascule de production, les sauvegardes et le
rollback. Complète [`render_setup.md`](render_setup.md) (variables d'env) et
[`architecture.md`](architecture.md).

> ⚠️ Aucune valeur secrète (URL complète, hostname Neon, mot de passe) ne doit
> figurer dans ce document, dans un commit ou dans les logs applicatifs. Les
> exemples ci-dessous utilisent des placeholders (`***`, `<host>`).

## 1. Architecture retenue

- **Neon** : projet `nextarget-prod`, région AWS **Frankfurt**, branche
  `production`, base `neondb`, version PostgreSQL par défaut de Neon.
- **Deux rôles** :
  - `neondb_owner` (propriétaire par défaut Neon) : réservé aux migrations
    Alembic et aux opérations d'administration (`pg_dump`/restauration).
  - `nextarget_app` (rôle applicatif dédié, créé manuellement) : privilèges
    minimaux — connexion + lecture/écriture sur le schéma applicatif
    uniquement, **pas** de droit de modification de schéma (`CREATE`/`ALTER`/
    `DROP`).
- **Deux variables d'environnement Render**, jamais commitées :
  - `DATABASE_URL` : connexion **poolée** (endpoint `-pooler`) du rôle
    `nextarget_app` — utilisée par l'application au runtime.
  - `DATABASE_MIGRATION_URL` : connexion **directe** (non poolée) du rôle
    `neondb_owner` — utilisée uniquement par Alembic et par `pg_dump`/`psql`
    pour la restauration/administration.
- **SQLite** reste utilisé pour le développement local et les tests unitaires
  (`DATABASE_URL=sqlite:///./data.db`, valeur par défaut). Aucun import des
  données SQLite de production : la bascule se fait sur une base Neon vide.
- **Alembic** est la source de vérité du schéma de production
  (`alembic/versions/`). `SQLModel.metadata.create_all()` (`init_db()`) ne
  s'exécute plus que si `DATABASE_URL` est du SQLite — voir
  `app/services/database.py`.
- Aucun workflow JavaScript Neon (`neon.ts`, `neon deploy`, MCP ou skills
  Neon) : la gestion reste 100 % Python (SQLModel + Alembic), pilotée depuis
  ce dépôt et le Dashboard Neon/Render.

## 2. Création du projet Neon (action manuelle, une fois)

1. Créer le projet Neon `nextarget-prod` (plan Free), région **Frankfurt**,
   base `neondb`.
2. Dans l'onglet **Roles**, créer le rôle applicatif `nextarget_app` avec un
   mot de passe généré par Neon (ne jamais le noter en clair ailleurs que
   dans le gestionnaire de secrets Render).
3. Accorder à `nextarget_app` uniquement les droits nécessaires sur le schéma
   `public` (connexion + `SELECT`/`INSERT`/`UPDATE`/`DELETE` sur les tables
   applicatives, aucun droit DDL). Exemple (à exécuter avec le rôle
   `neondb_owner`, une fois le schéma créé par Alembic — étape 3) :
   ```sql
   GRANT CONNECT ON DATABASE neondb TO nextarget_app;
   GRANT USAGE ON SCHEMA public TO nextarget_app;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nextarget_app;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public
     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nextarget_app;
   ```
4. Récupérer les deux chaînes de connexion depuis le Dashboard Neon :
   - **Pooled connection** (endpoint `-pooler`) du rôle `nextarget_app` →
     valeur de `DATABASE_URL`.
   - **Direct connection** du rôle `neondb_owner` → valeur de
     `DATABASE_MIGRATION_URL`.
   Les deux incluent `sslmode=require` (obligatoire chez Neon).
5. Renseigner ces deux valeurs dans le Dashboard Render (Environment), jamais
   dans `render.yaml` ni dans `.env` committé.

## 3. Bascule initiale (base vide, sans import de données)

La bascule s'effectue sur une base Neon **vide** — aucune donnée SQLite de
production n'est importée (décision NT-071).

1. Vérifier localement que la migration s'applique proprement sur une base
   Postgres jetable (voir §5 pour lancer un Postgres local de test) :
   ```bash
   export DATABASE_MIGRATION_URL=postgresql://localhost/nextarget_scratch
   alembic upgrade head
   ```
2. Une fois `DATABASE_URL`/`DATABASE_MIGRATION_URL` renseignées dans Render,
   déclencher un déploiement. `start.py` exécute `alembic upgrade head` avant
   Uvicorn : le schéma (`user`, `refreshtoken`) est créé sur Neon si les
   migrations réussissent ; **le service ne démarre pas** sinon (voir
   troubleshooting dans `render_setup.md`).
3. **Reconnexion obligatoire** : la bascule vide invalide de fait toutes les
   sessions/refresh tokens existants (l'ancienne base SQLite n'est plus
   utilisée). Chaque utilisateur doit se reconnecter une fois via Google ;
   son couple `(email, provider)` recrée un compte identique côté Neon (même
   logique `get_or_create_user`), sans doublon.
4. Vérifier en recette : créer un utilisateur, redéployer/mettre le service en
   veille puis le réveiller, confirmer que l'utilisateur et ses refresh
   tokens sont toujours présents.

## 4. Sauvegarde, restauration, rollback

### Sauvegarde manuelle (`pg_dump`, connexion directe)

```bash
# Utiliser DATABASE_MIGRATION_URL (rôle neondb_owner, connexion directe).
pg_dump "$DATABASE_MIGRATION_URL" -f backup_$(date +%Y%m%d%H%M).sql
```
- Ne jamais committer ce fichier ni le journaliser en clair (il ne contient
  pas le mot de passe, mais bien les données utilisateurs).
- Fréquence : avant toute migration de schéma en production, et
  périodiquement (l'automatisation récurrente est hors périmètre de NT-071,
  voir la note "tâches ultérieures" du backlog).

### Restauration

```bash
createdb -h <host> restore_check   # base de test dédiée, jamais la prod directement
psql "postgresql://.../restore_check?sslmode=require" -f backup_XXXX.sql -v ON_ERROR_STOP=1
```
Vérifier ensuite le contenu (`SELECT count(*) FROM "user";`) avant toute
restauration sur la base réelle.

### Rollback d'une migration Alembic

```bash
export DATABASE_MIGRATION_URL=...   # connexion directe, rôle neondb_owner
alembic current                     # révision actuellement appliquée
alembic downgrade -1                 # revient à la révision précédente
```
Pour un rollback complet post-bascule (retour à un état vide) :
`alembic downgrade base`. En cas de doute sur l'intégrité des données après un
rollback de schéma, restaurer plutôt depuis la dernière sauvegarde `pg_dump`.

## 5. Tester localement contre un vrai PostgreSQL

Aucune dépendance Docker n'est requise : un PostgreSQL local (Homebrew ou
autre) suffit.

```bash
createdb nextarget_test
export DATABASE_MIGRATION_URL=postgresql://localhost/nextarget_test
alembic upgrade head        # applique la migration initiale
alembic downgrade base      # vérifie le rollback complet

# Suite de tests dédiée (skip automatique si la variable est absente) :
export NEXTARGET_TEST_POSTGRES_URL=postgresql://localhost/nextarget_test
pytest tests/test_migrations_postgres.py tests/test_migrations_failure.py -v
```
La suite SQLite existante (`pytest`) reste la référence pour le
développement quotidien et ne nécessite aucune de ces variables.

## 6. Surveillance des quotas Neon Free

Le plan Neon Free impose des limites de calcul/stockage et une mise en veille
après inactivité (comparable à Render Free). Surveiller dans le Dashboard
Neon : heures de calcul consommées, taille de stockage, nombre de branches.
Aucune automatisation de suivi n'est mise en place par NT-071 (hors
périmètre) ; un dépassement se traduit par une dégradation ou une mise en
veille, pas par une perte de données.

## 7. Limites connues (héritées, non résolues par NT-071)

- Le rate limiter du coach (`services/rate_limiter.py`) et le state OAuth
  CSRF (`services/oauth_state.py`) restent **en mémoire, single-instance**.
  NT-071 corrige la persistance relationnelle (utilisateurs, refresh
  tokens) mais ne rend pas ces composants multi-instance (Redis nécessaire,
  hors périmètre).
- Un environnement Neon de staging distinct n'est pas mis en place par cet
  item.
