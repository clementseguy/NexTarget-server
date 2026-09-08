# Démo du Coach NexTarget

## 1. Finalité

La démo doit valider trois hypothèses :

- **Business** : un coach qui relie les sessions, les exercices et les objectifs apporte une valeur susceptible de justifier une offre payante.
- **Technique** : NexTarget peut produire et suivre un plan cohérent avec l’infrastructure et des modèles IA disponibles sur étagère.
- **Métier** : même sans expertise complète, un scénario étroit peut fournir des analyses, exercices et décisions suffisamment cohérents pour justifier un investissement ultérieur.

La proposition de valeur visée est :

```text
coach de session pertinent
+ coach de progression longitudinal
= utilisateur guidé vers son objectif
= valeur perçue pouvant soutenir une offre payante
```

La démo ne prouve pas encore la volonté de payer. Dans l’alpha, seuls les retours sur le coach de session seront recueillis auprès des utilisateurs du club. La valeur business propre au coach de progression restera donc une hypothèse illustrée, mais non validée auprès du marché.

## 2. Nature de la démo

La démo est un scénario vertical, limité et reproductible :

- un profil de tireur débutant ;
- un historique réel ou figé d’au moins cinq sessions ;
- cible C50, arme de poing, calibre et distance connus ;
- commentaires présents mais incomplets ;
- une seule priorité de travail ;
- un petit plan prédéfini ;
- quelques sessions suivantes permettant de montrer l’adaptation du plan.

Le coach de session conserve son fonctionnement actuel : un prompt IA analyse les données d’une session et de son exercice. Son rôle et son format de réponse sont modifiés.

Le coach de progression est une démonstration contrôlée : des règles `if/else` encadrent le scénario et un prompt IA produit l’analyse et la formulation. Il ne doit pas être présenté comme généralisable à tous les utilisateurs.

## 3. Objectifs de démonstration

La démo doit montrer que NexTarget peut :

1. produire un débrief de session plus précis et plus utile qu’aujourd’hui ;
2. comparer plusieurs sessions homogènes ;
3. identifier un à trois constats étayés et en prioriser un ;
4. proposer un plan composé d’un objectif, d’un exercice et d’un critère de réussite ;
5. suivre les tentatives liées au plan ;
6. distinguer objectif atteint, progression insuffisante et absence de progression ;
7. poursuivre, adapter ou arrêter le plan avec une justification claire.

## 4. Contraintes

### 4.1 Contraintes techniques

- Infrastructure actuelle : application, serveur Render et PostgreSQL Neon.
- Mistral comme fournisseur IA de l’alpha, derrière une interface interne pouvant être remplacée ultérieurement.
- Aucun RAG, base vectorielle ou fine-tuning.
- Aucun stockage ni analyse de photo dans la démo.
- Coût maîtrisé par des quotas fonctionnels, notamment l’interdiction d’analyser plusieurs fois la même progression sans nouvelle session.
- Une nouvelle analyse de progression exige au moins une nouvelle session éligible.
- La consultation du plan existant ne déclenche aucun appel IA.
- Interface fermée, sans saisie conversationnelle libre.

### 4.2 Contraintes métier

- Aucun entraîneur ne valide actuellement les diagnostics.
- Un seul historique utilisateur est disponible.
- Les exercices et décisions du scénario sont relus manuellement par le propriétaire du produit.
- Les conclusions s’appuient en priorité sur les données mesurables.
- Les commentaires et mesures déclarées par l’utilisateur sont pris en compte, avec un niveau de confiance inférieur et une formulation prudente.
- Les règles du stand et les recommandations d’un moniteur priment sur le coach numérique.

## 5. Ce que les données permettent réellement

Le formulaire fournit obligatoirement une taille de groupement en centimètres pour chaque série. L’utilisateur déclare le diamètre approximatif du cercle englobant les deux impacts les plus éloignés. Cette donnée permet d’analyser le groupement et sa régularité, mais elle n’a pas la même fiabilité qu’une mesure calculée automatiquement à partir des impacts.

Le coach peut analyser :

- le score normalisé ;
- la variation des scores entre séries ;
- la taille de groupement déclarée ;
- la variation des groupements entre séries et entre sessions ;
- l’évolution entre sessions comparables ;
- la réalisation d’un exercice ;
- la continuité d’un plan.

Le groupement est prioritaire sur le score pour un débutant lorsque les données indiquent qu’il n’est pas encore stabilisé.

Le coach peut exploiter les commentaires comme déclarations de l’utilisateur, sans les transformer en faits certains. Une douleur déclarée doit être rapportée comme telle, sans diagnostic médical ou technique.

## 6. Coach de session

### 6.1 Mission

Le coach de session débriefe uniquement la session terminée. Il ne crée pas de plan à long terme et ne change pas la priorité de coaching.

### 6.2 Données analysées

- Scores et nombre de tirs par série.
- Score total et score normalisé.
- Taille de groupement déclarée par série.
- Régularité des scores et des groupements entre les séries.
- Arme, calibre, distance, date et niveau déclaré.
- Commentaires de séries et de session.
- Prescription active et exercice associé, le cas échéant.
- Réalisation déclarée de l’exercice et respect du protocole.

### 6.3 Structure de réponse

#### Débrief

Résumé factuel du déroulement et des résultats. Les données objectives et déclaratives sont distinguées.

#### Réussites

Une à trois réussites maximum, appuyées sur les données mesurées ou déclarées. En l’absence de réussite identifiable, le coach valorise un comportement réel : session enregistrée, protocole suivi ou commentaire utile.

#### Point d’attention

Un seul point prioritaire observé pendant la session. Il ne devient pas automatiquement un nouvel objectif de coaching.

#### Évaluation de l’exercice

Si une prescription est active :

- réalisé, partiellement réalisé ou non réalisé ;
- critère atteint, en progression ou non atteint ;
- éléments objectifs et déclaratifs utilisés ;
- données manquantes.

#### Prochaine action

Continuer la prescription actuelle ou attendre la prochaine analyse du coach de progression. Le coach de session ne crée pas un nouvel exercice.

### 6.4 Exemple de réponse

> **Débrief** — Ton score normalisé est proche de ta référence récente. Les tailles de groupement que tu as renseignées sont plus homogènes, malgré une dernière série plus faible.
>
> **Réussites** — Tu as suivi l’exercice prévu et trois groupements déclarés sont plus homogènes que lors de la session précédente.
>
> **Point d’attention** — La baisse de la dernière série mérite d’être surveillée. Ton commentaire mentionne de la fatigue, sans permettre d’en confirmer la cause.
>
> **Exercice** — L’objectif n’est pas encore atteint, mais la métrique progresse. Conserve le même exercice pour une session supplémentaire.

## 7. Coach de progression simulé

### 7.1 Première analyse

Conditions :

- utilisateur connecté ;
- au moins cinq sessions éligibles ;
- C50, calibre, distance et barème identiques ;
- nombre de tirs connu ;
- changement d’arme accepté mais signalé comme facteur de confiance réduite.

Pour la démo, l’analyse utilise toutes les sessions éligibles. Cette décision simplifie le scénario actuel, fondé sur un historique limité.

Dans une future version ouverte aux utilisateurs, l’analyse devra utiliser une fenêtre fermée, par exemple les dix dernières sessions éligibles. La taille de cette fenêtre sera validée selon la pertinence métier, le coût et la taille du contexte envoyé au modèle.

La réponse contient :

1. un à trois constats issus des données mesurées ou déclarées ;
2. une seule priorité ;
3. la justification de cette priorité ;
4. un objectif mesurable ;
5. un exercice cohérent avec l’objectif ;
6. le nombre de sessions pendant lesquelles il doit être réalisé ;
7. un critère de réussite ;
8. les limites de l’analyse.

Pour la démo, les constats possibles sont limités à :

- taille et régularité des groupements déclarés ;
- régularité au sein des sessions ;
- stabilité des résultats entre sessions ;
- continuité de la pratique ou du plan.

Une session de référence représente 50 coups répartis en 10 séries, soit environ 45 à 60 minutes de travail. Le plan est exprimé uniquement en nombre de sessions, sans calendrier imposé.

### 7.2 Analyse récurrente

Conditions supplémentaires :

- au moins une nouvelle session éligible depuis la dernière analyse ;
- prescription active ;
- exercice marqué comme réalisé ou non réalisé.

La réponse :

1. rappelle l’objectif actif ;
2. compare la nouvelle mesure à la référence et à la session précédente ;
3. classe le résultat ;
4. justifie ce classement ;
5. applique la transition prévue.

### 7.3 États du résultat

- **Objectif atteint** : le critère final fixé par le plan est atteint et les données mesurées ou déclarées sont suffisantes.
- **Progression** : le critère final n’est pas atteint, mais le KPI s’améliore de plus de 3 % en variation relative dans le sens attendu.
- **Stable** : l’amélioration relative du KPI est comprise entre 0 et 3 %, ou le KPI reste inchangé.
- **Régression** : le KPI évolue dans le mauvais sens.
- **Non évaluable** : exercice non réalisé, protocole non suivi ou données insuffisantes.

Pour un KPI dont l’augmentation est favorable :

```text
variation_relative = (valeur_courante - valeur_reference) / valeur_reference × 100
```

Pour un KPI dont la diminution est favorable, comme la taille du groupement :

```text
variation_relative = (valeur_reference - valeur_courante) / valeur_reference × 100
```

Une valeur strictement supérieure à 3 % constitue une progression. Une valeur négative constitue une régression. Pour le groupement, la valeur comparée est le diamètre approximatif déclaré en centimètres.

Éviter l’expression « échec mais progression », contradictoire pour l’utilisateur.

### 7.4 Transitions de la démo

```text
Objectif atteint
→ clôturer l’objectif
→ lancer une nouvelle analyse des priorités

Progression
→ conserver le même exercice pendant au moins une session

Stable ou régression, première occurrence
→ proposer un exercice alternatif ou une variante simplifiée

Stable ou régression après adaptation
→ arrêter le plan
→ expliquer les limites du coach
→ recommander un moniteur local

Non évaluable
→ ne pas compter comme un échec
→ demander une nouvelle tentative exploitable
```

Cette règle accélérée sert la démonstration. Elle ne doit pas être considérée comme une règle métier validée pour le futur produit.

## 8. Plan et exercices de démonstration

La démo utilise un petit catalogue fermé de deux à quatre exercices. Aucun exercice n’est généré à la volée.

Chaque exercice possède :

- un objectif ;
- des prérequis ;
- des consignes ordonnées ;
- une durée indicative ;
- une mesure calculable par NexTarget ;
- un critère de réussite ;
- une variante simplifiée ;
- des limites et consignes de sécurité ;
- un statut « scénario de démonstration, non validé par un entraîneur ».

Chaque plan associe un exercice à un nombre de sessions. Chaque session est entièrement dédiée à cet exercice : 50 coups répartis en 10 séries. Le rythme calendaire reste libre.

Une session ne possède qu’une prescription principale. Cela évite d’attribuer un résultat à plusieurs exercices simultanés.

## 9. Scénario démontré

Pour garantir une démonstration reproductible, utiliser un compte de démonstration et un historique figé dérivé de données réelles.

### Acte 1 — Partir de l’existant

- L’utilisateur possède plusieurs sessions déjà analysées par le coach de session.
- Les analyses de session et leurs données sources sont disponibles pour le coach de progression.

### Acte 2 — Comprendre

- Affichage de cinq sessions historiques.
- Identification d’un à trois constats.
- Priorisation du groupement ou de sa régularité dans le scénario retenu.
- Présentation des preuves et limites.

### Acte 3 — Planifier

- Création d’un objectif mesurable.
- Prescription d’un exercice prédéfini.
- Plan de deux ou trois sessions d’environ 50 coups chacune.
- Activation automatique du plan après la première analyse.
- Aucun calendrier imposé.

### Acte 4 — Suivre

- Ajout d’une session montrant une progression sans atteinte de l’objectif.
- Débrief de session.
- Maintien de l’exercice.

### Acte 5 — Adapter

- Ajout d’une session stable ou en régression.
- Débrief de session.
- Remplacement ou simplification de l’exercice.

### Acte 6 — Clôturer

- Soit une nouvelle session atteint le critère et déclenche l’objectif suivant.
- Soit l’absence de progression après adaptation déclenche la recommandation d’un moniteur.

## 10. Persistance serveur

Les sessions doivent être synchronisées avant l’analyse, et non uniquement lorsque l’utilisateur demande un débrief. Sinon, l’historique transverse sera incomplet.

Toutes les sessions synchronisées et éligibles peuvent alimenter le coach de progression, qu’elles aient ou non déjà reçu un débrief du coach de session. Le scénario de démonstration utilise toutefois des sessions préalablement analysées pour rendre visible la continuité entre les deux coaches.

### Données normalisées

Conserver dans des entités relationnelles :

- session ;
- séries ;
- arme et calibre ;
- exercice ;
- objectif ;
- prescription ;
- tentative ;
- analyse.

### Instantané d’analyse

Conserver également un JSON immuable avec :

- sessions et métriques utilisées ;
- versions des règles, du prompt et du modèle ;
- décision structurée ;
- texte présenté.

La normalisation permet les comparaisons. L’instantané permet de reproduire et d’expliquer une analyse passée.

## 11. Interface fermée

Actions disponibles :

- lancer ma première analyse ;
- voir mon objectif et mon plan ;
- analyser ma progression ;

La réalisation de l’exercice et les informations nécessaires sont collectées dans le parcours de création de session, pas dans l’interface du coach de progression.

## 12. Usage de l’IA

### Coach de session

- conserve un appel IA fondé sur un prompt ;
- reçoit la session, l’exercice et les informations associées ;
- produit un débrief selon un schéma plus strict ;
- ne construit aucun plan longitudinal.

### Coach de progression

- reçoit l’historique des sessions et analyses éligibles ;
- utilise des conditions `if/else` pour encadrer les étapes du scénario ;
- appelle une IA pour analyser les éléments autorisés et rédiger la réponse ;
- refuse une nouvelle analyse de progression en l’absence de nouvelle session ;
- retourne le plan enregistré sans appel IA pour l’action « voir mon objectif et mon plan ».

Pour rendre la démo fiable :

- les métriques sont calculées par le serveur ;
- les décisions et transitions suivent une table de règles ;
- les exercices proviennent du catalogue fermé ;
- l’IA rédige les explications à partir d’un JSON imposé ;
- toute sortie invalide déclenche un texte déterministe ;
- une analyse identique n’est pas régénérée inutilement.

Mistral est conservé pour l’alpha. Le fournisseur IA doit être encapsulé derrière une interface simple afin de pouvoir comparer ultérieurement un autre modèle sans modifier la logique métier.

Un changement vers OpenAI ou Anthropic ne garantit pas à lui seul une amélioration majeure : la qualité dépend aussi des données, du prompt, des règles et des exercices. Un autre fournisseur ne sera testé que si Mistral échoue sur un jeu de cas NexTarget reproductible.

## 13. Critères d’acceptation

La démo est prête si :

- le scénario complet est rejouable sans modifier manuellement la base ;
- le coach de session ne propose jamais de plan ;
- le coach de progression ne produit qu’une priorité ;
- toute conclusion sur le groupement indique qu’elle repose sur une mesure déclarée par l’utilisateur ;
- chaque décision cite ses métriques et ses limites ;
- aucune nouvelle analyse récurrente n’est possible sans nouvelle session ;
- la consultation du plan ne déclenche aucun appel IA ;
- une session ou analyse rejouée ne crée pas de doublon ;
- le fallback fonctionne si le fournisseur IA échoue ;
- le parcours peut être présenté en moins de cinq minutes.

### Validation business

La démo du coach de progression n’étant pas ouverte aux utilisateurs du club, elle ne valide pas directement son intérêt business. Elle montre une proposition de valeur et permet de décider s’il est pertinent d’investir dans une version testable.

L’alpha du coach de session permet seulement de mesurer :

- compréhension et utilité du débrief ;
- confiance dans les observations ;
- qualité perçue par rapport à la version actuelle ;
- intérêt déclaré pour un futur suivi longitudinal.

Lorsque le coach de progression sera exposable, il faudra mesurer séparément :

À mesurer séparément :

- compréhension immédiate de la valeur ;
- utilité perçue du plan ;
- confiance dans les recommandations ;
- intention d’utiliser le coach après plusieurs sessions ;
- préférence entre une version gratuite limitée et une offre payante concrète ;
- prix ou modèle d’abonnement acceptable.

Une déclaration « je paierais » reste indicative. Le signal le plus fiable sera l’acceptation d’une offre réelle, d’une préinscription ou d’un essai payant.

## 14. Hors périmètre

- Coach généralisable à tous les profils.
- Expertise technique fine du geste ou de la posture.
- Analyse visuelle de la forme ou de la position du groupement.
- Vitesse et chronométrage.
- TAR.
- Génération autonome d’exercices.
- Référentiel scientifique de niveaux.
- Chat libre.
- Validation par un entraîneur.

## 15. Étapes immédiates

1. Figer l’historique et les différentes sessions du scénario.
2. Définir les métriques, dont celles du groupement déclaré, et les valeurs attendues.
3. Écrire la table de décisions et de transitions.
4. Écrire deux à quatre exercices de démonstration.
5. Définir les schémas serveur et synchroniser l’historique et les analyses de session.
6. Adapter le prompt et le contrat de sortie du coach de session.
7. Implémenter les règles `if/else` du coach de progression.
8. Ajouter l’appel IA du coach de progression derrière une interface fournisseur.
9. Tester le scénario complet, les quotas et le fallback.
10. Ouvrir uniquement le coach de session en alpha et recueillir les retours.
11. Utiliser la démo transverse pour décider si une version testable auprès des utilisateurs mérite d’être financée.
