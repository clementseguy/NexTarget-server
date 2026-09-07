# Architecture technique du MVP Coach NexTarget

## 1. Décision

Conserver l’infrastructure actuelle :

- application cliente existante ;
- API NexTarget sur Render Free ;
- PostgreSQL sur Neon Free ;
- Mistral par API ;
- règles métier et petit référentiel JSON versionnés dans le dépôt.

Aucune nouvelle infrastructure n’est obligatoire pour le MVP.

## 2. Contraintes de l’infrastructure gratuite

### Render

Render Free est adapté à un prototype, mais le service s’endort après 15 minutes d’inactivité et peut mettre environ une minute à redémarrer. Son système de fichiers est éphémère. Le service gratuit dispose de 750 heures mensuelles par workspace et peut être suspendu en cas de dépassement de certaines limites.

Conséquences :

- aucune donnée persistante sur le disque Render ;
- appels idempotents et relançables ;
- état du coaching enregistré dans Neon avant ou après toute opération critique ;
- attente visible dans l’application lors d’un démarrage à froid ;
- aucun worker permanent requis.

Source : [Render — Free services](https://render.com/docs/free).

### Neon

Neon Free convient au volume attendu : PostgreSQL, mise en veille automatique et 0,5 Go par projet selon l’offre publiée. Le transfert public inclus est limité ; les réponses doivent donc rester compactes.

Conséquences :

- index simples ;
- JSON limité aux traces d’analyse utiles ;
- pas de stockage d’images ;
- politique de rétention pour les prompts et réponses brutes ;
- migrations versionnées.

Sources : [Neon — Pricing](https://neon.com/pricing), [Neon — Network transfer](https://neon.com/docs/introduction/network-transfer).

## 3. Alternatives gratuites évaluées

| Service | Apport possible | Décision MVP |
|---|---|---|
| Cloudflare Workers Free | API sans mise en veille, 100 000 requêtes/jour | Ne pas migrer : limite de 10 ms CPU/invocation et coût de migration sans valeur fonctionnelle immédiate |
| Cloudflare AI Gateway | Logs, suivi des tokens/coûts, limitation, proxy Mistral | Option recommandée après le premier test fonctionnel |
| Cloudflare R2 | 10 Go/mois gratuits pour les photos | Différé avec l’analyse photo |
| Workers AI | Modèles gratuits dans certaines limites | Banc d’essai éventuel, pas de dépendance MVP |

Cloudflare AI Gateway prend officiellement en charge Mistral et ses fonctions principales sont proposées gratuitement. Il peut fournir une visibilité sur les requêtes, erreurs, tokens et coûts. Il faut toutefois désactiver ou éviter le cache pour les analyses personnalisées.

Sources : [AI Gateway et Mistral](https://developers.cloudflare.com/ai-gateway/usage/providers/mistral/), [AI Gateway — Pricing](https://developers.cloudflare.com/ai-gateway/reference/pricing/), [Workers — Limits](https://developers.cloudflare.com/workers/platform/limits/), [R2 — Pricing](https://developers.cloudflare.com/workers/platform/pricing/).

## 4. Architecture logique

```text
Application
  ├── saisie de session
  ├── intention et fréquence
  ├── affichage du débrief
  └── affichage du plan
          │
          ▼
API Render
  ├── authentification et consentement
  ├── stockage des sessions
  ├── calcul des métriques
  ├── règles de comparabilité
  ├── machine d’état du coaching
  ├── sélection des exercices
  ├── appel Mistral
  └── validation du JSON produit
          │
          ├────────► Neon PostgreSQL
          │
          └────────► Mistral API
                     via AI Gateway optionnel
```

## 5. Répartition code / IA

### Code déterministe

- normalisation des scores ;
- calcul de variabilité et d’assiduité ;
- sélection des sessions comparables ;
- compteur de tentatives et d’échecs ;
- transitions du plan ;
- exercices autorisés ;
- contrôle des seuils et des données manquantes.

### Mistral

- extraction prudente de thèmes dans les commentaires ;
- explication synthétique des résultats ;
- formulation de la priorité déjà déterminée ;
- adaptation du ton neutre ou exigeant ;
- rédaction du débrief et du plan dans un schéma imposé.

L’IA ne calcule pas les métriques, ne crée pas de seuil et ne décide pas seule des transitions.

## 6. Référentiel léger

Le dépôt contient des fichiers versionnés :

```text
coaching/
  skills.json
  exercises.json
  decision-rules.json
  comment-themes.json
  response-guidelines.json
```

Ils sont chargés au démarrage. Aucun RAG ni moteur de recherche vectorielle n’est nécessaire.

## 7. Modèle de données minimal

### `training_intent`

- utilisateur ;
- texte libre ;
- horizon en mois ;
- fréquence prévue ;
- statut.

### `coaching_objective`

- compétence ;
- métrique et référence initiale ;
- valeur cible ;
- nombre de sessions prévu ;
- niveau de confiance ;
- statut.

### `exercise`

- nom, catégorie et description ;
- compétence ;
- difficulté ;
- matériel ;
- consignes ordonnées ;
- prérequis ;
- type de mesure ;
- modèle de critère de réussite ;
- variante simplifiée ;
- statut de validation et version.

### `coaching_assignment`

- objectif et exercice ;
- copie du nom et des consignes ;
- valeur cible ;
- nombre de sessions ;
- état et compteurs.

### `exercise_attempt`

- session et prescription ;
- exercice réalisé ou non ;
- protocole suivi ou non ;
- valeur mesurée ;
- critère atteint, partiel ou non atteint ;
- retour utilisateur.

### `coach_analysis`

- type de coach ;
- sessions utilisées ;
- observations ;
- hypothèses synthétiques ;
- confiance et limites ;
- décision ;
- versions du prompt, du modèle et des règles ;
- texte affiché.

## 8. API minimale

```text
POST /sessions
GET  /coaching/status
POST /coaching/session-debrief
POST /coaching/progression-review
POST /coaching/assignments/{id}/attempt
POST /coaching/plan/pause
PUT  /training-intent
```

Les opérations d’analyse utilisent une clé d’idempotence. Une relance après démarrage à froid ne doit pas créer deux analyses ou deux prescriptions.

## 9. Stratégie d’appel Mistral

- Un appel après une session seulement si les données sont complètes.
- Un appel de progression seulement si de nouvelles sessions pertinentes existent ou si une transition est requise.
- Résultat mis en cache en base jusqu’à modification des données sources.
- Sortie JSON structurée validée côté serveur.
- Température basse.
- Taille maximale stricte du prompt et de la réponse.
- Modèle et prompt versionnés.
- Retour déterministe minimal si Mistral est indisponible.

La relecture par un second modèle n’est pas systématique dans le MVP. Les exercices sont validés en amont ; le serveur contrôle automatiquement les réponses.

## 10. Données, consentement et administration

- Consentement explicite avant synchronisation de l’historique.
- Identifiant technique pseudonyme dans les jeux d’évaluation.
- Suppression et export possibles.
- Commentaires considérés comme données personnelles potentielles.
- Pas de journalisation des secrets ni de la clé Mistral.
- Traces administrateur limitées à des justifications synthétiques : preuves, hypothèses, confiance, limites et décision.
- Pas de conservation d’un raisonnement interne détaillé du modèle.

## 11. Dégradation contrôlée

Si Render, Neon ou Mistral est indisponible :

- la session reste enregistrable localement ;
- la synchronisation est relançable ;
- le calcul local ou serveur affiche les métriques disponibles ;
- aucune nouvelle prescription n’est créée sans état serveur cohérent ;
- l’utilisateur reçoit un message explicite, sans réponse inventée.

## 12. Décision finale d’infrastructure

Render + Neon + Mistral suffisent au MVP. Ajouter Cloudflare AI Gateway devient pertinent uniquement pour mesurer les coûts, erreurs et tokens après validation de la première boucle fonctionnelle. Toute autre migration est différée jusqu’à l’apparition d’une limite mesurée.

