# Staging local de recette

Ce conteneur est l'environnement isolé de recette. La commande de
lancement récupère la branche demandée depuis `origin`, crée un worktree
détaché temporaire au commit récupéré, puis construit l'image depuis ce
worktree. Les modifications locales ne sont donc jamais incluses dans la
recette.

Sur le poste du runner :

```bash
cp .env.staging.example .env.staging
# Remplacer JWT_SECRET_KEY par une valeur locale aléatoire d'au moins 32 caractères.
scripts/staging_qa.sh up --branch dev
curl http://127.0.0.1:18000/health
```

`--branch` attend le nom d'une branche distante de `origin` et vaut `dev` par
défaut. Le script affiche le SHA exact exécuté ; il faut le conserver avec le
rapport de recette. Le serveur annonce ce SHA sur `/health` seulement en
staging. Le script serveur nécessite Git et Docker Compose.

Avant de lancer l'app pour une recette dépendant du serveur, remettre
explicitement les données de recette à zéro puis réinstaller les fixtures
déterministes :

```bash
scripts/staging_qa.sh reset
```

Cette commande ne s'exécute que si le conteneur utilise `ENVIRONMENT=staging`
et la base SQLite locale `/data/nextarget-staging.db`, imposés par Compose.
Elle recrée le schéma puis insère uniquement deux
exercices Coach de recette : `qa-catalog-precision-001` (actif) et
`qa-catalog-inactive-001` (inactif). Ces données ne sont ni des comptes, ni
des données de production, ni des fixtures publiées par une API d'administration.

Pour réinstaller ces fixtures sans supprimer l'état courant, utiliser :

```bash
scripts/staging_qa.sh fixtures
```

Après le reset, transmettre le SHA affiché au lanceur mobile depuis Yvain :

```bash
cd ../../hermes-knights-grail/yvain
bash scripts/run-android-staging.sh <SHA_DU_SERVEUR>
```

Le lanceur configure `adb reverse tcp:18000 tcp:18000`, impose une URL locale
au build DEBUG et vérifie le SHA depuis l'émulateur avant la recette. Il
nécessite Flutter, `adb`, `curl` et `jq`.

L'émulateur Android peut aussi atteindre ce serveur via
`http://10.0.2.2:18000` lorsqu'il n'utilise pas `adb reverse`. Aucun
identifiant OAuth ni secret Mistral n'est requis pour le premier périmètre hors
ligne.

Pour exécuter `pytest` dans le conteneur déjà en service, toujours isoler sa
base SQLite de celle du staging :

```bash
scripts/staging_qa.sh test
```
