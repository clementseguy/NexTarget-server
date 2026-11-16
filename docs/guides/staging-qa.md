# Staging local de recette

Ce conteneur est l'environnement isolé de recette. La commande de lancement
utilise une branche distante de `origin` ou une branche locale commitée, crée
un worktree détaché temporaire au commit choisi, puis construit l'image
depuis ce worktree. Les modifications non committées ne sont jamais incluses
dans la recette.

Sur le poste du runner :

```bash
cp .env.staging.example .env.staging
# Remplacer JWT_SECRET_KEY par une valeur locale aléatoire d'au moins 32 caractères.
scripts/staging_qa.sh up --branch staging
curl --fail http://127.0.0.1:18000/ready
```

`--branch` attend le nom d'une branche distante de `origin` et vaut `staging` par
défaut. Le script affiche le SHA exact exécuté ; il faut le conserver avec le
rapport de recette. Le serveur annonce ce SHA sur `/health` et `/ready`
seulement en staging. Le script serveur nécessite Git et Docker Compose.

Lancer cette recette après la fusion de `dev` dans `staging`, puis fusionner
`staging` dans `main` pour la release lorsque la recette est validée.

Pour utiliser les corrections conservées uniquement sur ce poste, créer un
commit local puis lancer la branche locale sans accès GitHub :

```bash
scripts/staging_qa.sh up --local-branch feature/NT-168-staging-qa
```

Les modifications non committées restent exclues de l'image.

`up` construit l'image, arrête l'ancien conteneur de ce projet Compose,
recrée sa base SQLite hors ligne, puis attend que `/ready` confirme le SHA,
la version du schéma de recette et les deux fixtures. Le volume peut être
conservé entre les lancements : ses anciennes tables et données sont
supprimées avant le démarrage. Si la reconstruction échoue, le lancement
échoue et l'API reste arrêtée. Ne lancer la recette qu'après la réussite de
`up` ou `reset`.

Compose impose `ENVIRONMENT=staging`, la base SQLite locale pour l'exécution
et les migrations, `DEBUG=false` et CORS vide, indépendamment du fichier
`.env.staging`. Le serveur refuse de démarrer en staging si l'une de ces
valeurs, le SHA source ou le secret JWT ne respecte pas le contrat local.
Le port HTTP est lié à `127.0.0.1` uniquement. Utiliser un secret JWT aléatoire
propre à la recette et ne pas placer d'identifiants de production dans
`.env.staging`.

`up` remet déjà les données à zéro. Pour revenir à l'état initial entre deux
scénarios, arrêter l'API, reconstruire la base et attendre sa disponibilité
avec :

```bash
scripts/staging_qa.sh reset
```

Cette commande ne s'exécute que si le conteneur a un SHA valide et utilise
la base SQLite locale `/data/nextarget-staging.db`, imposée par Compose.
Elle arrête l'API, supprime le fichier SQLite et ses fichiers WAL éventuels,
recrée le schéma puis insère uniquement deux
exercices Coach de recette : `qa-catalog-precision-001` (actif) et
`qa-catalog-inactive-001` (inactif). Ces données ne sont ni des comptes, ni
des données de production, ni des fixtures publiées par une API d'administration.
La commande refuse la remise à zéro si elle n'est pas exécutée dans son
conteneur de maintenance hors ligne. Les commandes de staging de ce poste
sont verrouillées pour éviter leur exécution simultanée.

`/health` vérifie seulement que le processus répond. `/ready` renvoie 200
uniquement si la base est accessible, marquée avec le SHA et la version de
schéma attendus, et contient les deux fixtures avec leurs états attendus.
Un échec renvoie 503 ; Compose l'utilise comme contrôle de santé. Hors staging,
`/ready` renvoie 404.

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

Pour vérifier le cycle Docker complet avant une campagne de recette :

```bash
bash tests/integration/test_staging_docker.sh
```

Ce test crée un projet Compose, un port, un volume et un dépôt Git local
temporaires. Il lance le serveur depuis le commit de la branche locale,
contrôle la configuration forcée par Compose, la disponibilité et les
fixtures, dégrade volontairement la base, vérifie le 503, puis teste `reset`
et un second `up`. Il supprime ses ressources à la fin. Il ne touche pas au
projet Compose habituel ni au conteneur `nextarget-server`. Les modifications
non committées ne sont pas incluses dans l'image testée : créer un commit local
avant son exécution. Aucun accès à GitHub n'est nécessaire pour ce test.
