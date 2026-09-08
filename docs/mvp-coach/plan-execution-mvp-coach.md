# Plan d’exécution fail fast du MVP Coach NexTarget

## 1. Principe

Tester d’abord les hypothèses qui peuvent invalider le produit :

- qualité des données, > faible aujourd'hui, manque d'utilisateurs (mais je peux recruter des users sur les forums. Cela implique que la priorité est d'enregistrer les sessions analysées par l'IA et de limiter l'utilisation de l'IA pour éviter les abus)
- pertinence des métriques, > nécessite des données
- capacité à choisir un exercice utile > nécessite une expertise (cf. documents de R&D de la NRA, armée US et française, etc.)
- stabilité des réponses IA (et comment tester ?)

Chaque étape produit un incrément testable. Aucun travail d’interface important ne précède la validation du moteur.

## 2. Étape -1 — Identifier et lever les prérequis de lancement

### Objectif

Éviter de développer le moteur sur un périmètre, des données ou des critères de
validation incomplets.

### Travail

- Auditer l'existant côté serveur, application et données.
- Distinguer les prérequis du pilote fermé de ceux du coach prescriptif.
- Affecter un responsable et une preuve de validation à chaque prérequis.
- Exécuter la checklist détaillée dans
  [`prerequis-lancement-mvp-coach.md`](prerequis-lancement-mvp-coach.md).

### Test de sortie

Tous les prérequis P0 ont un état, un responsable, une preuve attendue et aucun
blocage non arbitré. Le périmètre est aligné avec le backlog canonique.

### Arrêt ou pivot

Si le périmètre du premier pilote n'est pas figé, ne pas implémenter les modèles de
prescription et de plan. La collecte et la persistance des sessions peuvent en
revanche commencer, car elles sont communes aux deux périmètres.

## 3. Étape 0 — Constituer le jeu de test

### Objectif

Vérifier que les données existantes permettent réellement d’observer la régularité.

### Travail

- Extraire ou créer 20 à 30 sessions représentatives.
- Inclure données complètes, commentaires absents, changements d’arme et résultats irréguliers.
- Calculer manuellement le score normalisé et la variabilité.
- Rédiger pour chaque cas la conclusion attendue : données insuffisantes, référence, régularité à travailler ou continuité du plan.

### Test de sortie

Deux relectures du même cas à quelques jours d’intervalle aboutissent à la même conclusion principale.

### Arrêt ou pivot

Si les scores par série ne permettent pas de distinguer des cas utiles, ne pas développer le coach IA. Revoir la collecte de données en premier.

## 4. Étape 1 — Prototype déterministe hors production

### Objectif

Valider le cœur métier sans Mistral.

### Travail

- Normaliser les scores C50.
- Grouper les sessions par calibre et distance.
- Signaler les changements d’arme sans exclusion.
- Calculer variabilité et assiduité.
- Produire une priorité avec des règles configurables.
- Tester la machine d’état des échecs.

### Test de sortie

Le moteur retrouve la priorité attendue sur au moins 80 % du jeu de test, sans faux niveau de certitude.

### Arrêt ou pivot

Si les règles ne sont pas stables, ne pas intégrer Mistral : ajuster métriques, comparabilité ou données.

## 5. Étape 2 — Concevoir la petite base d’exercices

### Objectif

Vérifier qu’une prescription peut être claire et mesurable.

### Travail

- Créer 3 à 5 exercices de régularité.
- Créer 3 à 5 exercices de continuité du plan.
- Définir prérequis, protocole, durée, critère, variante simplifiée et cas d’incompatibilité.
- Relire manuellement chaque fiche.

### Test de sortie

Chaque priorité du jeu de test conduit à au moins un exercice compatible et à un résultat mesurable dans NexTarget.

### Arrêt ou pivot

Si un exercice exige une donnée absente, modifier l’exercice ou la saisie. Ne pas demander à l’IA de combler le manque.

## 6. Étape 3 — Persister les sessions et le coaching

### Objectif

Valider la boucle de données sur Render et Neon avant d’ajouter l’IA.

### Travail

- Remplacer les modèles Objectif et Exercice inutilisés.
- Ajouter intention, objectif de coaching, prescription, tentative et analyse.
- Synchroniser les sessions après consentement.
- Ajouter idempotence, migrations et suppression des données.
- Tester les démarrages à froid et les reprises réseau.

### Test de sortie

Un scénario complet fonctionne : session → prescription → tentative → résultat → transition, sans doublon après une relance.

### Arrêt ou pivot

Si Render Free rend le parcours inutilisable, mesurer la latence avant toute migration. N’envisager Cloudflare Workers ou un plan payant qu’avec un problème reproductible.

## 7. Étape 4 — Coach de session sans IA

### Objectif

Valider le rôle réduit et son utilité.

### Travail

- Générer un débrief par gabarits à partir des métriques.
- Afficher une observation principale.
- Évaluer la prescription active.
- Ne jamais modifier le plan.

### Test de sortie

Sur le jeu de test, aucun débrief ne contient plus d’une priorité et aucune conclusion ne dépasse les données disponibles.

### Arrêt ou pivot

Si le débrief déterministe est déjà suffisant, conserver cette solution et réserver l’IA au coach de progression.

## 8. Étape 5 — Ajouter Mistral au coach de session

### Objectif

Mesurer la valeur ajoutée réelle de l’IA.

### Travail

- Fournir à Mistral uniquement les métriques, commentaires et décisions autorisées.
- Exiger un JSON structuré.
- Valider le résultat côté serveur.
- Comparer gabarit déterministe et réponse IA en aveugle.

### Test de sortie

L’IA améliore la clarté ou la personnalisation sans réduire la justesse. Le schéma est valide dans au moins 98 % des appels de test.

### Arrêt ou pivot

Si Mistral ajoute peu de valeur, revenir aux gabarits. S’il hallucine, réduire son pouvoir de décision avant de changer de modèle.

## 9. Étape 6 — Coach de progression

### Objectif

Valider le coaching transverse sur plusieurs sessions.

### Travail

- Créer la phase de référence à partir de trois sessions.
- Créer un objectif, une prescription et un cycle.
- Convertir les sessions en semaines.
- Appliquer les transitions après les tentatives.
- Ne recalculer le plan que sur événement utile.

### Test de sortie

Les scénarios suivants passent automatiquement : progression, stagnation, deux échecs, trois échecs, quatre échecs, changement d’arme et session non comparable.

### Arrêt ou pivot

Si le plan change trop souvent, renforcer les règles de stabilité. S’il ne change jamais, revoir les seuils de transition.

## 10. Étape 7 — Évaluation des modèles et des coûts

### Objectif

Choisir le modèle le moins coûteux qui respecte la qualité attendue.

### Travail

- Comparer Mistral Small et un Ministral moins coûteux sur le même jeu de test.
- Mesurer validité JSON, justesse, répétition, latence, tokens et coût.
- Ajouter éventuellement Cloudflare AI Gateway pour l’observabilité et les limites de dépense.
- Fixer un plafond de tokens et un budget quotidien.

### Test de sortie

Le modèle retenu respecte les seuils de qualité et le coût maximal fixé.

### Arrêt ou pivot

Si aucun petit modèle n’est fiable, utiliser le modèle supérieur uniquement pour le coach de progression, moins fréquent, et garder le coach de session déterministe.

## 11. Étape 8 — Pilote utilisateur limité

### Objectif

Vérifier que le coach est compris et suivi.

### Travail

- Pilote avec 3 à 5 utilisateurs expérimentés.
- Mesurer utilité, clarté, faisabilité et répétition.
- Faire relire les exercices et les règles.
- Collecter les cas où le coach aurait dû s’abstenir.

### Critères de validation

- au moins 70 % des prescriptions jugées utiles et réalisables ;
- aucune prescription non mesurable ;
- aucune modification de plan sans raison enregistrée ;
- répétition toujours justifiée ;
- incidents et retours exploitables dans l’administration.

## 12. Ordre de développement recommandé

```text
Jeu de test
→ métriques déterministes
→ exercices validés
→ persistance serveur
→ boucle prescription/tentative
→ coach de session déterministe
→ comparaison avec Mistral
→ coach de progression
→ pilote utilisateurs
```

## 13. Travaux explicitement différés

- Photos et stockage objet.
- Création d’exercices à la volée.
- Second modèle relecteur systématique.
- RAG et base vectorielle.
- Référentiel de niveau externe.
- TAR, vitesse, posture et analyse avancée du matériel.
- Migration de Render ou Neon sans limite mesurée.
