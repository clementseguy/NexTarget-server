# Prérequis au lancement du MVP Coach IA

## 1. Décision de lancement recommandée

Le premier lancement doit être un **pilote fermé du coach de progression** : il
analyse plusieurs sessions comparables, restitue une observation prioritaire et
propose une prochaine action. Il ne crée pas encore automatiquement un objectif,
un exercice ou un plan.

Ce périmètre correspond au premier incrément du backlog canonique, réduit les
besoins d'expertise avant lancement et permet de collecter rapidement les données
qui manquent. Le coach prescriptif reste l'incrément suivant.

Deux niveaux de prérequis sont donc distingués :

- **P0** : obligatoire avant d'ouvrir le pilote fermé ;
- **P1** : obligatoire avant d'autoriser des prescriptions et adaptations de plan.

Une ouverture publique n'est pas couverte par cette checklist. Elle nécessitera
des seuils d'exploitation réévalués avec les résultats du pilote.

## 2. État constaté sur la branche

Au 7 septembre 2026 :

- l'API possède un seul endpoint Coach, `POST /coach/analyze-session` ;
- cet endpoint reçoit une session, envoie un prompt à Mistral et renvoie du texte
  libre ;
- aucune session, analyse, métrique, recommandation, consommation de tokens ou
  décision de coaching n'est persistée côté serveur ;
- le schéma PostgreSQL ne contient que les utilisateurs et refresh tokens ;
- la limite actuelle, 10 appels par utilisateur sur 5 minutes, est en mémoire,
  non configurable, non globale et remise à zéro à chaque redémarrage ;
- le serveur ne demande pas de sortie structurée à Mistral et ne valide pas le
  contenu métier de la réponse ;
- l'export disponible contient 22 sessions et 213 séries, toutes issues d'un seul
  utilisateur, dont seulement 2 sessions avec une ancienne analyse ;
- les 22 sessions ont des séries et des scores techniquement exploitables, mais
  elles couvrent seulement deux calibres, plusieurs libellés d'armes non
  normalisés et des distances parfois mélangées dans une même session ;
- le type de cible n'est pas enregistré. Il est donc impossible de prouver à
  partir des données que le barème C50 s'applique ;
- le client ne transmet pas actuellement la prise à une ou deux mains, la
  catégorie, le statut, les exercices associés, le type de cible ni un identifiant
  stable de session au serveur ;
- les sessions libres sans séries ne sont pas analysables avec les métriques de
  régularité retenues ;
- la suite de tests existe, mais l'environnement local observé ne contient pas
  d'exécutable `pytest` utilisable ; elle n'a donc pas pu être rejouée pendant cet
  audit documentaire.

Conclusion : les 22 sessions sont un bon jeu d'amorçage, mais pas une base de
validation représentative. Le premier chantier à livrer est la boucle de collecte
et de persistance, en parallèle du recrutement du pilote.

## 3. P0 — Prérequis produit et métier

### 3.1 Figer le contrat du pilote

- [ ] Écrire en une page la promesse : utilisateur cible, problème résolu, moment
  d'usage et résultat affiché.
- [ ] Confirmer que le pilote v1 produit un débrief de progression et une action
  suggérée, sans création automatique d'entité.
- [ ] Définir les deux compétences v1 : régularité et continuité de pratique.
- [ ] Confirmer les exclusions : photo, TAR, vitesse, posture, diagnostic médical,
  comparaison normative de niveau et chat libre.
- [ ] Aligner le périmètre avec le backlog canonique de `NexTarget-app` avant le
  développement. Les documents locaux ne doivent pas devenir un backlog parallèle.
- [ ] Nommer le responsable du go/no-go et le responsable de la validation métier.

**Sortie attendue :** périmètre signé, scénarios inclus/exclus et critères de
succès sans ambiguïté.

### 3.2 Définir précisément les données et métriques

- [ ] Produire un dictionnaire de données commun app/serveur avec nom, type, unité,
  caractère obligatoire, provenance et règle de validation de chaque champ.
- [ ] Ajouter un identifiant UUID stable généré sur l'appareil et une révision de
  session ; ne pas utiliser l'identifiant Hive local comme clé globale.
- [ ] Enregistrer explicitement le type de session, le statut, la cible et son
  barème, le calibre normalisé, la distance par série, l'arme, la prise, la
  catégorie, les exercices liés, les scores, le nombre de tirs et les commentaires.
- [ ] Définir quels brouillons, sessions libres, sessions incomplètes ou séries non
  scorées sont exclues de chaque calcul.
- [ ] Figer la formule de score normalisé, la métrique de variabilité, le traitement
  des séries de tailles différentes et les règles d'arrondi.
- [ ] Figer les clés de comparabilité. Minimum proposé : cible/barème, calibre et
  distance identiques ; changement d'arme ou de prise signalé et niveau de confiance
  réduit.
- [ ] Interdire le mélange silencieux de distances au sein d'un agrégat. Une session
  multi-distance doit produire plusieurs groupes ou être exclue avec un motif.
- [ ] Définir la fenêtre historique : maximum 10 sessions terminées et 90 jours,
  configurable et versionnée.
- [ ] Définir les données minimales : au moins 3 sessions comparables pour une
  tendance ; sinon réponse d'abstention et prochaine action de collecte.
- [ ] Définir amélioration, stagnation, régression, cas atypique, données
  insuffisantes et niveau de confiance.
- [ ] Ne pas présenter les seuils provisoires comme des normes scientifiques.

**Sortie attendue :** spécification versionnée, exemples calculés à la main et
tests unitaires correspondants.

### 3.3 Définir la responsabilité du coach

- [ ] Écrire les décisions autorisées et interdites pour chaque endpoint.
- [ ] Limiter chaque réponse à une observation prioritaire, ses preuves, ses limites
  et une prochaine action.
- [ ] Définir les motifs d'abstention : données insuffisantes ou incohérentes,
  demande médicale, situation dangereuse, contenu hors tir sportif ou tentative de
  détournement du prompt.
- [ ] Afficher que les règles du stand et les consignes de l'encadrant priment et
  que le coach ne remplace pas un instructeur.
- [ ] Faire dépendre le ton uniquement de la formulation. La décision et le niveau
  de confiance doivent être identiques pour toutes les personas.

**Sortie attendue :** matrice décisions/données/preuves/abstentions utilisable
dans les tests.

## 4. P0 — Collecte et base de connaissances

### 4.1 Quantité minimale de données

Il n'est pas nécessaire d'attendre une grande communauté pour lancer un pilote.
Les seuils ci-dessous sont des **gates d'ingénierie provisoires**, pas des seuils
statistiques scientifiques :

- [ ] conserver les 22 sessions actuelles comme données d'amorçage d'un seul
  utilisateur ;
- [ ] constituer un corpus de référence de 30 à 50 cas annotés, combinant sessions
  réelles consenties et cas synthétiques de bord ;
- [ ] recruter au minimum 5 utilisateurs pilotes, avec si possible 3 sessions
  comparables historiques chacun avant leur première analyse de progression ;
- [ ] couvrir au moins : historique insuffisant, progression, stagnation,
  régression, forte variabilité, changement d'arme, changement de prise,
  multi-distance, données manquantes, valeur aberrante et commentaire trompeur ;
- [ ] réserver des cas de test qui ne servent jamais à ajuster les règles ou les
  prompts afin d'éviter une validation sur les données d'entraînement ;
- [ ] annoter chaque cas avec sessions retenues/exclues, métriques attendues,
  conclusion principale, conclusions interdites, confiance et motif d'abstention.

**Gate pilote :** 30 cas annotés relus, dont au moins 15 cas réels issus d'au
moins 3 utilisateurs. Le recrutement des 5 utilisateurs peut continuer pendant le
développement ; il ne bloque pas la construction du pipeline.

### 4.2 Modèle de persistance recommandé

Ne pas créer une base vectorielle et ne pas dénormaliser toutes les sessions comme
unique source de vérité. PostgreSQL suffit :

- tables relationnelles normalisées `training_session` et `training_series` pour
  l'état courant, liées à `user.id` ;
- table `coach_analysis` avec un **instantané JSON immuable et borné** des données
  réellement analysées ;
- colonnes structurées/indexables pour les recherches fréquentes ; JSONB seulement
  pour l'instantané, les métriques dérivées et la sortie structurée ;
- référentiels de règles et libellés versionnés dans le dépôt, sans RAG.

L'instantané d'analyse doit contenir : identifiants et révisions des sessions,
empreinte du contenu, métriques calculées, règles de sélection, données manquantes
et consentement applicable. Il garantit la reproductibilité sans remplacer les
tables métier.

La ligne d'analyse doit aussi conserver : utilisateur, type d'analyse, statut,
clé d'idempotence, version de schéma, version des règles, version du prompt, modèle
exact, paramètres, horodatages, latence, tokens entrée/sortie, coût estimé, sortie
validée, texte affiché, fallback utilisé, erreur catégorisée et feedback utilisateur.
Ne pas conserver un raisonnement interne détaillé du modèle.

### 4.3 Synchronisation app/serveur

- [ ] Ajouter un consentement explicite, versionné et révocable avant tout import.
- [ ] Séparer consentement au fonctionnement du coach et réutilisation dans un jeu
  d'évaluation/amélioration.
- [ ] Créer une API batch d'import/upsert bornée, authentifiée et idempotente.
- [ ] Définir la résolution de conflit à partir de la révision, pas de l'heure du
  téléphone seule.
- [ ] Définir la propagation des modifications et suppressions, avec tombstone si
  nécessaire pour éviter la résurrection hors ligne.
- [ ] Retourner le statut de chaque élément d'un batch : créé, mis à jour, inchangé,
  rejeté avec motif.
- [ ] Ne synchroniser que les données nécessaires au périmètre v1 ; exclure les
  photos.
- [ ] Conserver localement une file de synchronisation reprenable avec backoff et
  état visible.
- [ ] Ne lancer une analyse que sur une révision synchronisée et cohérente.
- [ ] Invalider le cache d'analyse si une session source est modifiée ou supprimée.

**Sortie attendue :** import historique puis création, modification, suppression
et rejeu réseau sans doublon ni perte.

## 5. P0 — Moteur déterministe avant IA

- [ ] Implémenter côté serveur la validation métier, la comparabilité, la
  normalisation, la variabilité et la sélection de fenêtre.
- [ ] Retourner les mêmes résultats quel que soit l'ordre des sessions reçues.
- [ ] Produire une décision structurée avant l'appel IA : priorité, preuves,
  confiance, limites, abstention éventuelle et prochaine action autorisée.
- [ ] Versionner les règles et seuils ; toute analyse référence leur version.
- [ ] Prévoir un fallback déterministe lisible lorsque Mistral est indisponible,
  invalide ou hors quota.
- [ ] Vérifier le moteur sur le corpus annoté avant de travailler le style des
  prompts.

**Gate :** au moins 90 % de conclusions principales conformes sur le corpus de
référence et 100 % des cas dangereux/hors périmètre en abstention. Le seuil de 90 %
est provisoire et devra être confirmé par le pilote.

## 6. P0 — Contrat IA et évaluation

- [ ] Remplacer la réponse texte libre par un schéma Pydantic/JSON Schema versionné.
- [ ] Utiliser le mode `json_schema` de Mistral, puis revalider la réponse côté
  serveur. Les sorties structurées personnalisées sont recommandées par Mistral
  pour imposer types et valeurs attendues :
  [documentation Mistral](https://docs.mistral.ai/studio/conversations/structured-output).
- [ ] Séparer données système, décision déterministe et textes utilisateurs ; les
  commentaires libres sont du contenu non fiable, jamais des instructions.
- [ ] Fixer température, limite de tokens, timeout, nombre maximal de nouvelles
  tentatives et comportement de fallback.
- [ ] Épingler une version de modèle pour le pilote. Ne pas utiliser seulement un
  alias `-latest` sans campagne de non-régression.
- [ ] Tester au minimum deux exécutions par cas et persona pour mesurer stabilité,
  conformité, contradictions et répétition.
- [ ] Comparer en aveugle formulation déterministe et formulation IA ; conserver
  l'IA seulement si elle améliore clarté ou personnalisation sans réduire la
  justesse.
- [ ] Définir les rubriques d'évaluation : exactitude par rapport aux métriques,
  respect du périmètre, abstention, actionnabilité, ton, absence de promesse et
  absence de conseil dangereux.
- [ ] Mettre les échecs de production exploitables dans une file de revue
  pseudonymisée, seulement si le consentement correspondant existe.

**Gates :** 100 % de réponses conformes au schéma après validation/fallback, zéro
conseil dangereux dans le corpus, aucune métrique inventée, et décision identique
entre personas.

## 7. P0 — Vie privée, sécurité et droits utilisateur

- [ ] Définir finalité, base légale, responsable de traitement, sous-traitants,
  destinataires, durées de conservation et procédure d'incident avant collecte.
- [ ] Mettre à jour l'information utilisateur avec les traitements serveur et
  Mistral. La CNIL recommande de définir la finalité, minimiser les données et
  réaliser un pilote à petite échelle :
  [recommandations CNIL](https://www.cnil.fr/fr/developpement-des-systemes-dia-les-recommandations-de-la-cnil-pour-respecter-le-rgpd).
- [ ] Vérifier les conditions Mistral applicables à la conservation et à la
  réutilisation des données pour le compte et l'offre effectivement utilisés.
- [ ] Décider explicitement si les mineurs sont exclus du pilote ; recommandation :
  les exclure tant que le consentement et l'encadrement ne sont pas cadrés.
- [ ] Implémenter export, suppression de compte, suppression des données Coach et
  retrait du consentement, puis tester ces parcours de bout en bout.
- [ ] Définir une rétention courte pour les entrées/sorties brutes et une rétention
  distincte pour les agrégats techniques.
- [ ] Chiffrer les flux, garder les secrets en environnement, appliquer le moindre
  privilège PostgreSQL et vérifier qu'aucun prompt/commentaire/token n'entre dans
  les logs.
- [ ] Tester l'isolation entre utilisateurs sur toutes les routes par IDOR, y
  compris import, lecture, analyse, export et suppression.
- [ ] Borner textes, listes et payloads ; neutraliser prompt injection, HTML/Markdown
  dangereux et contenu hors périmètre.

**Sortie attendue :** notice approuvée, registre interne, parcours de droits testé
et revue sécurité sans anomalie critique.

## 8. P0 — Coûts, quotas et anti-abus

- [ ] Rendre configurables les limites par utilisateur, globale par jour et globale
  par mois.
- [ ] Persister les compteurs ou réservations de budget dans PostgreSQL ; la limite
  mémoire actuelle ne protège pas après redémarrage et ne plafonne pas la dépense
  globale.
- [ ] Dédupliquer par empreinte des entrées et clé d'idempotence avant l'appel
  Mistral.
- [ ] Refuser la régénération si aucune donnée source pertinente n'a changé, sauf
  action administrateur auditée.
- [ ] Enregistrer les tokens retournés par le fournisseur et calculer le coût selon
  une table de prix versionnée.
- [ ] Fixer un budget mensuel et des seuils d'alerte à 50 %, 80 % et 100 % ; à 100
  %, activer le fallback, jamais une dépense implicite.
- [ ] Ajouter un kill switch des appels IA indépendant des autres fonctions.
- [ ] Protéger import et analyse contre concurrence, payload géant et rafales.

**Gate :** un test de rejeu/concurrence ne provoque qu'un appel facturable et le
budget maximal est techniquement impossible à dépasser de façon non bornée.

## 9. P0 — Fiabilité, exploitation et déploiement

- [ ] Créer les migrations Alembic, index, contraintes, clés étrangères et rollback.
- [ ] Tester les migrations sur un PostgreSQL réel, sauvegarde puis restauration.
- [ ] S'assurer que toute opération critique est transactionnelle et reprenable.
- [ ] Ajouter des timeouts distincts DB/fournisseur, retry uniquement sur erreurs
  transitoires et circuit breaker simple.
- [ ] Mesurer latence totale, temps de réveil, erreurs DB/Mistral, taux de fallback,
  JSON rejetés, tokens, coût, cache hit, abstentions et feedback.
- [ ] Créer des alertes sur erreurs, coût, migrations et saturation de connexions.
- [ ] Ajouter un readiness check qui vérifie la base sans exposer de secret ; garder
  le health check léger.
- [ ] Tester le parcours à chaud, après mise en veille, pendant une indisponibilité
  Neon/Mistral et pendant un redéploiement.
- [ ] Afficher côté app une attente et une relance sans duplication. Render indique
  qu'un service Free s'arrête après 15 minutes d'inactivité et redémarre en environ
  une minute ; son disque est éphémère :
  [documentation Render](https://render.com/docs/free).
- [ ] Vérifier les limites réelles des comptes avant le pilote. Neon Free annonce
  actuellement 0,5 Go par projet et 5 Go/mois de transfert public :
  [tarifs Neon](https://neon.com/pricing),
  [transfert réseau](https://neon.com/docs/introduction/network-transfer).
- [ ] Écrire le runbook : désactiver l'IA, rollback applicatif, rollback de migration,
  restaurer la base, traiter une fuite et contacter les pilotes.

**Gate :** scénario complet réussi sur l'environnement de pilote après démarrage à
froid, puis restauration testée et kill switch vérifié.

## 10. P0 — Tests et critères de go/no-go

- [ ] Tests unitaires : validation, unités, arrondis, comparabilité, métriques,
  sélection de fenêtre, confiance, abstention et cache.
- [ ] Tests d'intégration : PostgreSQL, migration, sync, idempotence, concurrence,
  suppression et autorisations.
- [ ] Tests de contrat app/serveur et Mistral avec réponses valides, invalides,
  vides, tronquées, lentes et en erreur.
- [ ] Tests de sécurité : accès croisé, injection dans commentaires, dépassement de
  taille, rate limit, secrets et rendu Markdown.
- [ ] Tests de non-régression du corpus à chaque changement de règle, prompt ou
  modèle.
- [ ] Charge légère sur le volume du pilote et mesure à chaud/froid.
- [ ] CI verte, couverture des nouveaux chemins critiques et aucun appel réel à
  Mistral dans la suite standard.

Le pilote peut ouvrir seulement si tous les critères suivants sont vrais :

- [ ] périmètre, métriques, comparabilité et abstentions validés ;
- [ ] import et consentement fonctionnels ;
- [ ] sessions et analyses persistées avec versions et idempotence ;
- [ ] corpus minimal et gates de qualité atteints ;
- [ ] quotas persistants, budget, kill switch et fallback testés ;
- [ ] export/suppression et isolation utilisateurs testés ;
- [ ] monitoring, alertes, sauvegarde/restauration et runbook opérationnels ;
- [ ] cinq pilotes recrutés, informés, consentants et avec canal de support ;
- [ ] formulaire de feedback séparant compréhension, utilité, faisabilité et
  sécurité ;
- [ ] aucun défaut critique ouvert.

## 11. P1 — Prérequis du coach prescriptif

Ces éléments ne doivent pas bloquer le premier pilote informatif, mais deviennent
obligatoires avant toute prescription ou adaptation automatique de plan :

- [ ] faire valider par une personne compétente un référentiel de 6 à 10 exercices ;
- [ ] pour chaque exercice : objectif, niveau, matériel, sécurité, protocole, durée,
  mesure, critère, variante, incompatibilités, auteur, version et validation ;
- [ ] conserver un instantané de l'exercice dans chaque prescription ;
- [ ] définir objectifs de coaching, prescriptions, tentatives et leurs états ;
- [ ] spécifier toutes les transitions, acteurs autorisés et invariants de la
  machine d'état ;
- [ ] ne compter un échec que si exercice réalisé, protocole suivi et mesure
  disponible ;
- [ ] obtenir une validation explicite de l'utilisateur avant toute création ou
  modification d'objectif, exercice ou plan ;
- [ ] tester progression, stagnation, deux/trois/quatre échecs, pause, reprise,
  changement de contexte et recommandation d'un instructeur ;
- [ ] ajouter invalidation administrative, désactivation d'exercice et audit des
  changements.

## 12. Ce qui ne bloque pas le pilote fermé

- grand nombre d'utilisateurs ou centaines de sessions ;
- RAG, base vectorielle ou fine-tuning ;
- stockage et analyse de photos ;
- second modèle relecteur ;
- Cloudflare AI Gateway ;
- interface d'administration complète ;
- migration immédiate vers un autre hébergeur ;
- plan Render payant, tant que la latence mesurée reste acceptable pour les pilotes.

## 13. Ordre d'exécution le plus court

Lancer quatre chantiers en parallèle après validation du périmètre :

1. **Contrats** : dictionnaire de données, métriques, comparabilité, schémas JSON et
   critères d'abstention.
2. **Collecte** : consentement, UUID stable, import/upsert et recrutement de cinq
   pilotes.
3. **Serveur** : tables sessions/séries/analyses, idempotence, quotas persistants et
   métriques déterministes.
4. **Évaluation/exploitation** : annotation de 30 cas, harness de régression,
   budget, monitoring, kill switch, suppression et runbook.

Puis intégrer Mistral uniquement comme couche de formulation structurée, exécuter
les gates, et ouvrir le pilote. Les exercices et plans sont développés après les
premiers retours, sauf décision explicite d'élargir le MVP.
