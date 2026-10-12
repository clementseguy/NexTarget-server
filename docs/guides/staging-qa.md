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
rapport de recette. Il nécessite Git et Docker Compose sur le poste du runner.

L'émulateur Android atteint ce serveur via `http://10.0.2.2:18000`. Aucun
identifiant OAuth ni secret Mistral n'est requis pour le premier périmètre hors
ligne.

Pour exécuter `pytest` dans le conteneur déjà en service, toujours isoler sa
base SQLite de celle du staging :

```bash
scripts/staging_qa.sh test
```
