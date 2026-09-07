# Périmètre du MVP Coach NexTarget

## 1. Objectif

Valider qu’un coaching simple, fondé sur plusieurs sessions, apporte plus de valeur qu’une analyse isolée générée par un prompt unique.

Le MVP doit aider un tireur à suivre une méthode sur plusieurs séances. Il ne cherche pas encore à devenir un expert universel du tir sportif.

## 2. Décisions de cadrage

- Tir d’entraînement généraliste sur cible papier C50.
- Arme de poing uniquement.
- Barème de 0 à 10 par tir.
- Photos, chronométrage, analyse de posture et TAR hors MVP.
- Deux compétences seulement : régularité et assiduité/continuité du plan.
- Interface fermée, sans chat libre.
- L’objectif personnel peut être saisi librement, puis reformulé sous une forme structurée.
- Les sessions sont enregistrées sur le serveur avec consentement.
- Les données liées à un compte sont pseudonymisées, pas qualifiées d’anonymes.

## 3. Deux coaches aux responsabilités exclusives

### 3.1 Coach de session : débriefer

Il intervient après une session et :

1. résume les résultats ;
2. compare la session aux sessions comparables ;
3. relève un seul fait significatif ;
4. évalue la prescription en cours ;
5. indique l’action prévue pour la prochaine session.

Il ne crée pas de plan, ne change pas d’objectif et ne remplace pas seul un exercice.

### 3.2 Coach de progression : décider et planifier

Il analyse plusieurs sessions et :

1. choisit la compétence prioritaire ;
2. crée ou révise un objectif de coaching ;
3. sélectionne un exercice validé ;
4. définit un cycle en nombre de sessions ;
5. traduit ce cycle en semaines selon la fréquence de pratique ;
6. décide de poursuivre, simplifier, remplacer ou réévaluer le plan.

Il est le seul composant autorisé à modifier le plan.

## 4. Objectifs

Le modèle actuel peut être remplacé sans rétrocompatibilité.

### 4.1 Intention personnelle

Définie par l’utilisateur :

- texte libre ;
- horizon de 1 à 12 mois ;
- fréquence prévisionnelle de pratique ;
- statut actif, atteint, abandonné ou remplacé.

Exemple : « Dans trois mois, je veux améliorer ma régularité. »

Cette intention cadre le plan, mais ne remplace pas l’analyse des résultats.

### 4.2 Objectif de coaching

Défini par le coach :

- compétence visée ;
- état initial ;
- métrique ;
- valeur cible ;
- nombre de sessions prévues ;
- statut ;
- justification synthétique.

Exemple : réduire la variabilité des scores par série sur deux sessions consécutives.

La gamification et les anciens « achievements » sortent du chemin critique du MVP.

## 5. Données nécessaires

### 5.1 Session

- date ;
- calibre ;
- distance ;
- cible C50 ;
- nombre de tirs et score de chaque série ;
- score total ;
- commentaire libre par série et par session ;
- exercice et prescription associés, le cas échéant.

L’arme est conservée comme contexte, mais une différence d’arme n’exclut pas une session du panel MVP.

### 5.2 Comparabilité

Dans le MVP, des sessions sont comparables si elles partagent :

- le calibre ;
- la distance ;
- la cible C50 ;
- le barème de 10 points maximum par tir.

Une différence d’arme diminue le niveau de confiance et doit être signalée, sans exclure la session.

### 5.3 Métriques déterministes

```text
score_maximal = nombre_de_tirs × 10
score_normalisé = score / score_maximal × 100
variabilité_session = écart-type des scores normalisés par série
assiduité = sessions_réalisées / sessions_prévues
```

Les seuils restent configurables. Ils ne doivent pas être présentés comme des références scientifiques avant validation.

## 6. Exercices : décision MVP

Une petite base d’exercices doit être construite avant le coaching en production.

- 6 à 10 exercices au total ;
- couvrant uniquement régularité et continuité du plan ;
- relus manuellement par le propriétaire du produit ;
- protocole, prérequis et critère de réussite obligatoires ;
- variantes simples prévues quand c’est utile.

Le coach sélectionne et paramètre ces exercices. Il ne crée pas d’exercice inédit à la volée dans le MVP.

Raison : sans référentiel humain initial, un second appel IA ne constitue pas une validation experte fiable. La génération pourra être ajoutée plus tard dans un espace administrateur, avec revue avant publication.

## 7. Cycle de coaching

1. Moins de trois sessions comparables : constitution de la référence.
2. À partir de trois sessions : création possible d’un premier plan, avec confiance faible.
3. Exercice réalisé et critère atteint : consolidation.
4. Deux échecs consécutifs : exercice alternatif ou protocole simplifié.
5. Trois échecs : réévaluation de l’objectif et des hypothèses.
6. Quatre échecs : recommandation de consulter un instructeur.

Un échec n’est compté que si l’exercice a été réalisé, le protocole suffisamment suivi et la mesure disponible.

## 8. Interface

Le coach de progression propose uniquement des actions guidées :

- analyser ma progression ;
- voir mon plan ;
- comprendre ma priorité ;
- déclarer une difficulté ;
- mettre le plan en pause ;
- modifier mon intention personnelle ou ma fréquence prévue.

La seule saisie libre autorisée concerne l’intention personnelle et les commentaires de session.

## 9. Hors périmètre

- Analyse de photos et de groupements géométriques.
- Vitesse et cadence objectives.
- Diagnostic certain de posture, prise en main ou geste.
- Comparaison normative débutant/confirmé/expert.
- TAR et autres disciplines spécialisées.
- RAG, base vectorielle, fine-tuning et génération libre d’exercices.
- Promesse de progression dans un délai garanti.

## 10. Critères de succès

Le MVP est validé si :

- il produit une priorité stable et explicable sur un panel de sessions ;
- il évite les changements ou répétitions non justifiés ;
- chaque exercice prescrit possède un résultat mesurable ;
- le cycle complet prescription → tentative → résultat → adaptation fonctionne ;
- les utilisateurs jugent le conseil clair, pertinent et réalisable ;
- une progression de la régularité ou de l’assiduité peut être mesurée.

