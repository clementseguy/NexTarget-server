# Autres sujets à cadrer pour le MVP Coach NexTarget

## 1. Conclusion de l’audit

Les sujets ci-dessous doivent être tranchés progressivement.

## 2. Décisions bloquantes avant le développement

### 2.1 Définitions métier exactes

Il faut figer :

- le nombre minimal de séries et de tirs pour calculer la régularité ;
- la formule exacte de variabilité ;
- la fenêtre historique utilisée : trois, cinq ou davantage de sessions ;
- les seuils provisoires faible, moyenne et forte variabilité ;
- la définition d’une amélioration, d’une stagnation et d’une régression ;
- le nombre de sessions de confirmation avant de valider un objectif ;
- le traitement d’une session atypique ou incomplète.

Décision proposée : placer tous les seuils dans une configuration versionnée et les qualifier de provisoires jusqu’au pilote.

### 2.2 Comparabilité des sessions

Le MVP accepte un changement d’arme, mais celui-ci peut fausser l’analyse. Il faut définir :

- les différences qui excluent une session ;
- celles qui réduisent seulement la confiance ;
- l’effet exact d’un changement d’arme ;
- le comportement lorsque moins de trois sessions strictement comparables existent ;
- la manière d’afficher cette limite à l’utilisateur.

Décision proposée : calibre, distance, cible C50 et barème identiques sont obligatoires. L’arme différente applique un indicateur de confiance réduite.

### 2.3 Définition de l’assiduité

L’assiduité ne peut pas être calculée sans planning de référence. Il faut décider :

- fréquence déclarée ou fréquence historiquement observée ;
- délai toléré autour d’une session prévue ;
- gestion des vacances, blessures et pauses volontaires ;
- distinction entre session manquée et plan mis en pause ;
- moment où une absence devient un échec de continuité.

Décision proposée : utiliser la fréquence déclarée, avec pause explicite et aucune pénalisation pendant la pause. Ne pas employer de vocabulaire culpabilisant.

### 2.4 Cycle de vie complet du plan

Les états et transitions doivent être exhaustifs :

```text
draft
active
paused
adapting
reevaluating
completed
abandoned
human_review_recommended
```

Il faut définir qui peut déclencher chaque transition, les données obligatoires et les transitions interdites.

### 2.5 Contrat des exercices

Avant de rédiger les 6 à 10 exercices, fixer un schéma obligatoire :

- compétence principale ;
- niveau et prérequis ;
- matériel ;
- consignes ;
- durée ;
- mesure attendue ;
- critère de réussite ;
- variante simplifiée ;
- incompatibilités ;
- règles de sécurité ;
- auteur, version et validation.

Il faut aussi décider qui peut modifier un exercice déjà associé à un plan. La prescription doit conserver un instantané pour rester reproductible.

### 2.6 Contrats d’entrée et de sortie des coaches

Les schémas JSON complets doivent être écrits avant les prompts :

- données autorisées en entrée ;
- champs obligatoires ;
- valeurs d’enum ;
- limites de taille ;
- niveau de confiance ;
- motifs d’abstention ;
- erreurs récupérables ;
- réponse de secours sans IA.

Le texte utilisateur doit toujours être dérivé d’une décision structurée validée par le serveur.

## 3. Données et synchronisation

### 3.1 Migration des sessions locales

Il faut décider :

- si les anciennes sessions sont envoyées au serveur ;
- à partir de quelle date ;
- comment obtenir le consentement ;
- comment éviter les doublons ;
- quelle source gagne en cas de conflit ;
- si une session supprimée localement doit être supprimée du serveur.

Décision proposée : import explicite, identifiant stable généré sur l’appareil et API idempotente.

### 3.2 Mode hors connexion

Le comportement doit être défini quand le serveur est indisponible :

- session enregistrée localement ;
- synchronisation différée ;
- état visible ;
- nouvelle tentative automatique ou manuelle ;
- absence de prescription tant que l’état serveur n’est pas cohérent.

### 3.3 Qualité des données

Prévoir des contrôles sur :

- score supérieur au maximum ;
- nombre de tirs nul ;
- séries manquantes ;
- distance ou calibre absent ;
- doublon de session ;
- commentaire vide ou excessivement long ;
- incohérence entre total et séries.

Le coach doit s’abstenir lorsque les données sont insuffisantes.

### 3.4 Conservation et suppression

Fixer une politique pour :

- sessions ;
- commentaires ;
- analyses produites ;
- prompts et réponses brutes ;
- journaux techniques ;
- jeux d’évaluation pseudonymisés.

Définir les procédures d’export, suppression du compte et retrait du consentement.

## 4. Sécurité et responsabilité

### 4.1 Périmètre de sécurité

Le coach doit rester limité au tir sportif en stand et rappeler que :

- les règles du stand et les consignes de l’encadrant priment ;
- une analyse à distance ne remplace pas un instructeur ;
- il doit s’abstenir face à une situation dangereuse, médicale ou hors périmètre ;
- il ne doit pas transformer un commentaire ambigu en conseil technique certain.

### 4.2 Utilisateurs mineurs

Décider si les mineurs sont autorisés et, le cas échéant, quelles règles de consentement et d’encadrement s’appliquent.

### 4.3 Contenus libres

L’intention et les commentaires restent libres. Il faut prévoir :

- longueur maximale ;
- filtrage des demandes hors périmètre ;
- protection contre les instructions visant à détourner le prompt ;
- absence d’exécution d’actions à partir du texte libre ;
- journalisation prudente des contenus personnels.

## 5. Expérience utilisateur

### 5.1 Onboarding

Définir le parcours initial :

1. consentement à la synchronisation ;
2. saisie de l’intention et de l’horizon ;
3. fréquence prévue ;
4. explication des limites du coach ;
5. collecte d’au moins trois sessions comparables ;
6. création du premier plan.

### 5.2 Cas sans données suffisantes

Le coach doit fournir une prochaine action utile sans inventer de diagnostic : enregistrer de nouvelles sessions comparables, compléter une donnée ou poursuivre le plan existant.

### 5.3 Ton

Les tons neutre et exigeant doivent partager exactement la même décision. Il faut écrire des règles éditoriales et des exemples interdits : culpabilisation, certitude excessive, promesse de résultat ou agressivité.

### 5.4 Explicabilité

Définir deux niveaux :

- utilisateur : raisons courtes, données utilisées et limites principales ;
- administrateur : observations, règles déclenchées, hypothèses, confiance, versions et décision.

## 6. Administration et exploitation

### 6.1 Administration minimale

Même sans interface complète, il faut pouvoir :

- consulter une analyse et ses versions ;
- désactiver un exercice ;
- modifier un seuil ;
- invalider une prescription ;
- relancer une analyse ;
- exporter un cas vers le jeu d’évaluation ;
- couper tous les appels IA avec un kill switch.

Une commande ou une route protégée suffit au MVP.

### 6.2 Observabilité

Mesurer au minimum :

- latence totale et démarrage à froid ;
- taux d’erreur Render, Neon et Mistral ;
- consommation de tokens et coût ;
- taux de JSON invalide ;
- fréquence du fallback déterministe ;
- nombre d’analyses par utilisateur ;
- répétition des conseils ;
- transitions de plan.

Cloudflare AI Gateway peut être ajouté après la première boucle fonctionnelle. Il ne remplace pas les métriques métier stockées dans NexTarget.

### 6.3 Budget et quotas

Fixer avant le pilote :

- budget IA mensuel maximal ;
- limite quotidienne globale ;
- limite par utilisateur ;
- taille maximale des prompts ;
- nombre maximal de régénérations ;
- comportement lorsque le quota est atteint.

Décision proposée : fallback déterministe et aucune facturation implicite.

## 7. Tests et qualité

### 7.1 Jeu de référence

Chaque cas doit contenir :

- sessions d’entrée ;
- métriques attendues ;
- sessions retenues ou exclues ;
- priorité attendue ;
- exercice acceptable ;
- conclusions interdites ;
- niveau de confiance attendu.

### 7.2 Tests nécessaires

- unitaires sur les métriques et transitions ;
- intégration API et Neon ;
- migrations et idempotence ;
- synchronisation hors ligne ;
- contrats JSON Mistral ;
- régression des prompts et modèles ;
- autorisations d’accès aux données ;
- charge légère et latence sur Render Free.

### 7.3 Critères chiffrés

Les critères actuels doivent être complétés par :

- taux minimal de décisions métier correctes ;
- taux maximal de JSON invalide ;
- taux maximal d’abstention incorrecte ;
- latence acceptable à chaud et à froid ;
- coût maximal par analyse ;
- taux minimal d’exercices jugés réalisables ;
- taux maximal de répétitions non justifiées.

## 8. Déploiement et pilote

### 8.1 Feature flags

Prévoir des indicateurs indépendants pour :

- synchronisation des sessions ;
- coach de session ;
- coach de progression ;
- appels Mistral ;
- ton exigeant.

Ils permettent une activation progressive et un arrêt rapide.

### 8.2 Déploiement progressif

Ordre recommandé :

1. compte de développement ;
2. données synthétiques ;
3. données personnelles du propriétaire ;
4. un ou deux utilisateurs volontaires ;
5. pilote de trois à cinq utilisateurs ;
6. ouverture plus large après revue.

### 8.3 Retour utilisateur

Après chaque analyse, recueillir séparément :

- conseil compris ;
- conseil jugé utile ;
- exercice réalisable ;
- raison d’un avis négatif.

Un score global seul ne permet pas de corriger le système.

## 9. Décisions pouvant attendre le pilote

- analyse des photos ;
- création d’exercices par IA ;
- second modèle relecteur ;
- référentiel normatif débutant, confirmé et expert ;
- comparaison stricte par arme ;
- TAR ;
- migration hors Render ou Neon ;
- gamification et achievements.

## 10. Checklist avant le premier développement

- [ ] Formule et seuils provisoires de régularité définis.
- [ ] Règles de comparabilité définies.
- [ ] Assiduité et pauses définies.
- [ ] Machine d’état complète définie.
- [ ] Schémas des exercices et prescriptions définis.
- [ ] Contrats JSON des deux coaches définis.
- [ ] Politique de synchronisation et consentement définie.
- [ ] Règles de sécurité et d’abstention définies.
- [ ] Budget et quotas IA définis.
- [ ] Jeu initial de cas de test disponible.
- [ ] Feature flags et kill switch prévus.

## 11. Priorité immédiate

Avant toute intégration Mistral, produire quatre artefacts :

1. le dictionnaire des données de session ;
2. la spécification des métriques et seuils provisoires ;
3. les schémas JSON des exercices, prescriptions et analyses ;
4. dix cas de test annotés manuellement.

Ces artefacts réduisent le risque principal : développer une couche IA sur des décisions métier encore ambiguës.

