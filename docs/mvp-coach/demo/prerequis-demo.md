# Prérequis techniques de la démo Coach NexTarget

## 1. Principes retenus

- Le coach de session reste un appel IA fondé sur un prompt.
- Le coach de progression combine règles `if/else` et appel IA.
- Toutes les sessions consenties sont synchronisées pour la démo.
- Une session possède zéro ou un exercice.
- Un exercice peut être utilisé dans zéro à plusieurs sessions.
- Une session d’exercice contient 50 coups répartis en 10 séries.
- Le plan est exprimé en nombre de sessions.
- Le premier plan devient actif automatiquement.
- Une nouvelle analyse de progression exige une nouvelle session éligible.
- La progression est calculée par rapport à la référence initiale du plan.

## 2. Corrections de la liste initiale

### 2.1 Relation session–exercice

La cardinalité correcte est :

```text
Session 0..1 ─── 0..n Exercise
```

En base, la solution la plus simple est un `exercise_id` nullable dans `session`. Une table de jointure n’est pas nécessaire pour la démo.

La session doit aussi pouvoir référencer la prescription active. L’exercice indique ce qui est réalisé ; la prescription indique pourquoi et selon quel critère.

### 2.2 Sessions enregistrées

Le serveur ne doit pas enregistrer uniquement les sessions analysées. Toutes les sessions autorisées et éligibles doivent être synchronisées, sinon l’historique du coach de progression sera incomplet.

L’analyse du coach de session est un objet distinct, relié à la session.

### 2.3 Relation avec l’utilisateur

Le coach de progression doit retrouver les sessions d’un utilisateur. Une relation persistante est donc obligatoire.

Chiffrer ou hacher simplement l’identifiant ne rend pas les données anonymes. Tant que les sessions peuvent être rattachées à un compte, elles sont pseudonymisées.

Solution recommandée pour la démo :

- identifiant utilisateur interne opaque, différent de l’adresse email ;
- clé étrangère vers cet identifiant ;
- contrôle d’accès systématique par utilisateur ;
- aucune donnée d’identité dans les prompts ou journaux ;
- suppression des données à la demande.

Une table de correspondance séparée ou un HMAC n’est utile que si l’architecture d’authentification actuelle le justifie.

### 2.4 Type de coach

Le paramètre fonctionnel permettant de choisir arbitrairement un « type de coach » peut être supprimé.

En revanche, il faut conserver une distinction technique entre :

- analyse de session ;
- analyse initiale de progression ;
- analyse récurrente de progression.

Cette distinction peut être portée par des endpoints séparés et un champ `analysis_kind` défini par le serveur. Elle ne doit pas être choisie librement par le client.

Le ton éventuel du coach est une préférence séparée. Il ne doit pas modifier les décisions métier.

## 3. Modifications obligatoires dans l’application

### 3.1 Identifiants et synchronisation

- Générer un UUID stable pour chaque session et chaque série.
- Conserver cet identifiant lors des nouvelles tentatives de synchronisation.
- Afficher l’état local : non synchronisée, synchronisation en cours, synchronisée ou erreur.
- Réessayer sans créer de doublon.
- Synchroniser les sessions historiques après consentement.

### 3.2 Modèle de session

Ajouter ou garantir :

- `userId` implicite via l’authentification ;
- `exerciseId` nullable ;
- `prescriptionId` nullable ;
- arme ;
- calibre ;
- distance ;
- cible C50 ;
- niveau d’expérience au moment de la session ;
- 10 séries et 50 coups pour les sessions d’exercice de la démo ;
- score et nombre de tirs par série ;
- diamètre approximatif du groupement en centimètres par série ;
- commentaires de série et de session ;
- dates de création et de modification.

Le serveur recalcule les métriques. Il ne doit pas faire confiance aux valeurs dérivées envoyées par l’application.

### 3.3 Relation exercice–session

- Remplacer la relation plusieurs-à-plusieurs actuelle ou envisagée par `Session.exerciseId?`.
- Empêcher l’association de plusieurs exercices dans l’interface.
- Lorsqu’un plan est actif, préremplir l’exercice prescrit.
- Conserver dans la session l’identifiant de la prescription suivie.

### 3.4 Parcours de création de session

Le parcours doit demander :

- exercice prescrit réalisé : oui ou non ;
- protocole suivi : oui, partiellement ou non ;
- éventuel commentaire sur l’exercice.

Ces données permettent de distinguer une absence de progression d’une tentative non évaluable.

### 3.5 Coach de session

La requête doit contenir :

- identifiant de session ;
- données complètes de la session et des séries ;
- arme, calibre, distance et niveau ;
- exercice et prescription associés ;
- commentaires ;
- métriques calculées ou recalculables.

La réponse suit un contrat structuré :

- débrief ;
- une à trois réussites ;
- un point d’attention ;
- évaluation de l’exercice ;
- prochaine action autorisée ;
- limites de l’analyse.

### 3.6 Coach de progression

Limiter l’interface à :

- lancer ma première analyse ;
- voir mon objectif et mon plan ;
- analyser ma progression.

Prévoir les états suivants :

- aucune donnée suffisante ;
- première analyse disponible ;
- plan actif ;
- nouvelle session requise ;
- progression analysable ;
- plan terminé ;
- recommandation d’un moniteur.

### 3.7 Niveau d’expérience

Déplacer le niveau dans les préférences ou le profil de coaching.

- Valeurs contrôlées : débutant, confirmé, expérimenté, inconnu.
- Le champ ne doit pas bloquer la création d’une session.
- La valeur utilisée doit être copiée dans l’instantané d’analyse pour conserver le contexte historique.

### 3.8 Consentement

Une simple case booléenne ne suffit pas pour assurer la traçabilité.

Enregistrer :

- version du texte accepté ;
- date d’acceptation ;
- date de retrait éventuel ;
- état de synchronisation ;
- choix de suppression ou de conservation des données déjà envoyées.

Le retrait bloque toute nouvelle synchronisation.

## 4. Modifications obligatoires sur le serveur

### 4.1 API de synchronisation

Créer une opération idempotente de création ou mise à jour d’une session :

```text
PUT /sessions/{clientSessionId}
```

Le serveur :

- récupère l’utilisateur depuis l’authentification ;
- vérifie le consentement ;
- valide les données ;
- recalcule les totaux et métriques ;
- crée ou met à jour sans doublon ;
- interdit l’accès aux sessions d’un autre utilisateur.

### 4.2 Persistance minimale

Objets obligatoires :

```text
UserCoachingConsent
Session
Series
Exercise
SessionAnalysis
CoachingObjective
CoachingPlan
Prescription
ExerciseAttempt
ProgressionAnalysis
```

### 4.3 Catalogue d’exercices

Le serveur devient la source de vérité pour les deux à quatre exercices de démonstration.

Chaque exercice possède :

- compétence ;
- consignes ;
- prérequis ;
- nombre de coups et de séries ;
- KPI ;
- critère de réussite ;
- variante simplifiée ;
- version ;
- statut actif ou désactivé.

L’application peut conserver une copie locale pour l’affichage et le mode hors connexion.

### 4.4 Coach de session

Endpoint recommandé :

```text
POST /sessions/{sessionId}/analysis
```

Le serveur :

- vérifie la propriété de la session ;
- construit les métriques ;
- charge l’exercice et la prescription ;
- construit le prompt ;
- appelle Mistral ;
- valide la réponse structurée ;
- enregistre l’analyse et les versions utilisées ;
- renvoie un fallback si l’appel échoue.

Une analyse existante est renvoyée si les données sources et les versions n’ont pas changé.

### 4.5 Première analyse de progression

Endpoint recommandé :

```text
POST /coach/progression/initial-analysis
```

Le serveur :

- vérifie qu’aucun plan actif n’existe ;
- charge toutes les sessions éligibles de la démo ;
- exige au moins cinq sessions ;
- calcule les KPI ;
- applique les règles `if/else` ;
- appelle Mistral avec les décisions autorisées ;
- crée et active automatiquement objectif, plan et prescription ;
- enregistre la référence initiale du KPI.

### 4.6 Consultation du plan

```text
GET /coach/progression/plan
```

Cette opération lit uniquement la base. Elle ne déclenche aucun appel IA.

### 4.7 Analyse récurrente

```text
POST /coach/progression/analysis
```

Le serveur :

- vérifie qu’un plan est actif ;
- exige une nouvelle session éligible depuis la dernière analyse ;
- vérifie que la session référence la prescription ;
- classe la tentative ;
- calcule la variation relative par rapport à la référence initiale ;
- applique les transitions `if/else` ;
- appelle Mistral pour produire la justification ;
- enregistre l’analyse et la dernière session évaluée.

### 4.8 Calcul des KPI

Pour un KPI dont l’augmentation est favorable :

```text
progression = (valeur_courante - valeur_initiale) / valeur_initiale × 100
```

Pour la taille du groupement :

```text
progression = (groupement_initial - groupement_courant) / groupement_initial × 100
```

Classification :

- progression : résultat strictement supérieur à 3 % ;
- stable : résultat compris entre 0 et 3 % ;
- régression : résultat négatif ;
- non évaluable : exercice non réalisé, protocole non suivi ou données insuffisantes.

Le groupement d’une session doit être calculé à partir des dix diamètres déclarés selon une formule à fixer avant le développement : moyenne, médiane ou autre agrégat.

### 4.9 Machine d’état

Implémenter dans le code, pas dans le prompt :

```text
objectif atteint
→ clôturer le plan

progression
→ conserver la prescription

stable ou régression, première occurrence
→ activer la variante ou l’exercice alternatif

stable ou régression après adaptation
→ clôturer le plan
→ recommander un moniteur

non évaluable
→ conserver le plan sans compter un échec
```

### 4.10 Fournisseur IA

Créer une interface interne minimale :

```text
AiProvider.generateSessionAnalysis(...)
AiProvider.generateProgressionAnalysis(...)
```

L’implémentation alpha utilise Mistral. Il n’est pas nécessaire d’implémenter un second fournisseur.

### 4.11 Validation des réponses IA

- Sortie JSON structurée.
- Schéma distinct pour chaque analyse.
- Refus des champs inconnus.
- Limites de longueur.
- Valeurs d’enum contrôlées.
- Fallback déterministe.
- Versions du modèle et du prompt enregistrées.
- Aucun texte IA utilisé pour modifier directement la base sans validation métier.

## 5. Sécurité obligatoire

- Authentification requise pour tous les endpoints de coaching.
- Autorisation vérifiée sur chaque session, plan et analyse.
- Identifiants opaques non séquentiels.
- Clé Mistral uniquement côté serveur.
- Aucune donnée d’identité envoyée au fournisseur IA.
- Commentaires non écrits dans les journaux applicatifs.
- Limitation du nombre d’analyses par utilisateur et par session.
- Protection contre la réutilisation d’une session d’un autre compte.
- Endpoint ou procédure de suppression des données de coaching.

## 6. Contrôle des coûts

Les limites fonctionnelles suffisent pour la démo :

- une analyse de session par version de session ;
- une première analyse de progression par plan ;
- une analyse récurrente uniquement après une nouvelle session ;
- consultation du plan sans IA ;
- pas de régénération libre ;
- taille maximale des commentaires et du contexte ;
- compteur des tokens et appels par utilisateur.

## 7. Tests obligatoires

### Application

- Association de zéro ou un exercice.
- Session d’exercice à 10 séries et 50 coups.
- Consentement accordé et retiré.
- Synchronisation, erreur réseau et nouvelle tentative.
- Affichage des trois actions du coach de progression.

### Serveur

- Idempotence de la synchronisation.
- Isolation stricte entre utilisateurs.
- Validation des scores, tirs et groupements.
- Calcul des KPI et de la variation relative.
- Référence initiale immuable pendant le plan.
- Refus d’une analyse sans nouvelle session.
- Transitions du plan.
- Réponse IA valide, invalide, en erreur et expirée.
- Absence d’appel IA lors de la consultation du plan.

### Scénario de démonstration

- Première analyse sur au moins cinq sessions.
- Plan activé automatiquement.
- Première nouvelle session en progression.
- Deuxième session stable ou en régression.
- Adaptation de l’exercice.
- Réussite ou recommandation d’un moniteur.

## 8. Déploiement obligatoire

- Migrations Neon réversibles.
- Feature flag pour le nouveau coach de session.
- Feature flag et liste blanche pour le coach de progression.
- Coach de progression accessible uniquement au compte de démonstration.
- Kill switch des appels IA.
- Affichage explicite « version alpha » pour les utilisateurs testeurs du coach de session.

## 9. Ordre d’implémentation recommandé

1. Figer les KPI, leur agrégation et les données du scénario.
2. Définir les schémas de données et réponses JSON.
3. Implémenter consentement, identifiants et synchronisation.
4. Persister sessions, séries et exercices.
5. Adapter la relation session–exercice et le parcours de session.
6. Modifier le coach de session et enregistrer ses analyses.
7. Ajouter objectif, plan, prescription et tentative.
8. Implémenter les règles du coach de progression sans IA.
9. Ajouter le prompt Mistral du coach de progression.
10. Ajouter quotas, feature flags, fallback et tests du scénario.

## 10. Décisions restant à prendre

1. Agrégat du groupement d’une session : moyenne ou médiane des dix séries.
2. Définition exacte du KPI de régularité du groupement.
3. Suppression immédiate ou conservation des données déjà synchronisées après retrait du consentement.
4. Comportement si une session historique ne contient pas exactement 10 séries ou 50 coups.
5. Structure actuelle de l’authentification et identifiant interne disponible.

