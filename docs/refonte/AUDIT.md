# Refonte Radar — audit et périmètre livré

Base examinée : `ce0d00fc8dd6a8a8b591de60e2025daf243dd36b`.
Travail sur `refactor/radar-product-security`. Aucune connexion à une base de production, aucun paiement, aucune migration de production, aucun déploiement.

## Problèmes identifiés et corrections

| Constat dans le dépôt | Conséquence | Traitement |
| --- | --- | --- |
| `change-plan`, `toggle-addon`, `toggle-pack` écrivaient directement les droits | Auto-attribution de fonctionnalités payantes | Demande persistée séparée de la décision ; anciennes bascules refusées |
| Administration globale accordée par `role=admin` | Confusion entre agence et plateforme | Activation et gestion globale des utilisateurs réservées à `is_superuser` |
| Calculs différents par plan, packs, addons et frontend | Droits incohérents entre écran et API | Catalogue et droits effectifs dans `core/subscription.py` ; frontend consomme les API |
| Expiration non utilisée pour autoriser les API | Accès payant après expiration | Repli vers Core dans les droits effectifs |
| `workspace_id` fourni sans validation dans certaines routes agence | Lecture d’une autre organisation | Résolveur commun avec contrôle propriétaire/membre, même pour un rôle admin |
| Détails projet et enfants chargés uniquement par ID | Lecture/modification interentreprises | Vérification du parent et filtre ORM de Session par workspace |
| Relations projet historiques avec `workspace_id=NULL` | Risque de masquer des projets existants | Appartenance héritée du client, conservée comme référence pour ces lignes |
| Assignees et autres références étrangères non validés systématiquement | Association à un collaborateur ou objet d’une autre agence | Validation des références et refus des écritures des viewers |
| Cache serveur indexé uniquement par utilisateur | Résultats d’un workspace réutilisés dans un autre | Ajout du workspace aux clés concernées ; nouveau préfixe des événements vérifiés |
| État d’abonnement persisté et cache React Query partagé | Droits ou données précédents après changement de compte | Abonnement en mémoire, remise à zéro à la déconnexion, client de cache par identité/workspace |
| Requêtes `fetch` et Axios sélectionnaient des workspaces différents | Interface incohérente pour un utilisateur multi-agence | Helper `workspaceFetch` pour les requêtes natives, cohérent avec Axios |
| Prédictions commerciales remplaçaient les échecs API par budgets/opportunités fictifs | Présentation de faux résultats comme réels | Interface archivée ; API et chemins alternatifs de prédiction commerciale suspendus |
| Carte générant des concerts déterministes sans source | Événements fictifs en production | État vide ou 503 ; code générateur conservé, sans appel en production |
| Fans Deezer convertis en followers/listeners Spotify | Confusion entre mesures et estimations | Suppression de la conversion pour les nouvelles collectes, provenance et données manquantes explicites |
| Cachet optimal et confiance chiffrée non validée | Précision trompeuse | Fourchette indicative, confiance non calibrée, absence de tarif si aucune observation |
| Projections artistiques non évaluées | Aucune mesure d’erreur historique | Évaluation chronologique du modèle existant, comparaison au dernier niveau observé, aucune précision inventée si historique insuffisant |
| Références de devis/factures uniques globalement mais générées par workspace | Collision entre entreprises et créations concurrentes | Unicité par entreprise et compteurs transactionnels, sans renumérotation |
| Suppression de factures émises possible hors statut payé | Perte d’historique | Suppression limitée aux brouillons |
| Deux modèles fusionnaient `opportunity_tags` | Métadonnées ORM incompatibles | Association moderne séparée, copie conditionnelle, dictionnaire historique conservé |
| Types PostgreSQL homonymes pour tâches anciennes et tâches agence | Statuts incompatibles | Modèles agence alignés sur les colonnes VARCHAR des migrations existantes |
| Import `Field` manquant dans la facturation | Import de l’application impossible | Import réparé |
| Tests acceptant un 401 inattendu | Faux succès fonctionnels | Tests remplacés par des assertions de parcours réels ; ancienne suite conservée pour audit |
| Versions Next.js, Axios, MapLibre vulnérables | Risques de sécurité signalés par npm | Mise à niveau ; justification détaillée dans VALIDATION.md |

## Inventaire et décisions fonctionnelles

| Domaine / modules existants | Décision et parcours final | Niveau de vérification |
| --- | --- | --- |
| Core : `agency_projects`, `agency_tasks`, `project_detail`, `assets`, calendrier, inbox | Conservés ; `/today` principal ; un projet relie déjà tâches, livrables, fichiers, activité ; création interne possible sans ouvrir le CRM | Tests de création, modification, enfants et isolation ; intégrations Google non exercées en direct |
| Dashboards `/dashboard`, `/cockpit`, `/today` | Entrées publiques fusionnées vers `/today`, anciens écrans archivés | Typage et build |
| Recherche artistes `/artist`, `/artists`, `/spotify-search`, Discovery | Entrée `/discovery` ; recherche nom/URL, file asynchrone, fiche `/discovery/[id]`, sélections `/comparison` ; services existants conservés | Autorisation, fiche sans données et reprise sur erreur testées ; fournisseurs réels non validés |
| Artistes : enrichissement et popularité | Conservés ; sources/dates, estimations, données manquantes ; évaluation `/artist-predictions/{nom}/evaluation` | Tests d’absence de fuite temporelle et d’historique insuffisant ; aucune calibration commerciale revendiquée |
| Events | Nouveau lien léger vers les projets existants, artistes Discovery, lieu/dates et budget prévisionnel ; dépenses Business ; carte accessible dans ce contexte | Création et transfert d’artiste, droits financiers et isolation testés ; montage réel d’événement à valider en recette |
| Prestations, responsables, contrats | Réutilisation des tâches, livrables, responsables et fichiers du projet de production | Pas de nouveau logiciel métier parallèle ; recette métier complète encore nécessaire |
| Business : CRM, pipeline, devis/factures/paiements | Conservés, réservés à Business ; suivi des paiements existant, sans fausse transaction de prestataire | Test devis → acceptation → facture → paiement ; isolation et numérotation par entreprise |
| Banque / Revolut | Reportés, API suspendues et navigation retirée ; code et données conservés | Aucune validation bancaire ou PSD2 revendiquée |
| Veille concurrentielle autonome | Désactivée dans le parcours public ; code conservé | Navigation et API de son module suspendues |
| Prédictions de gain commercial | Suspendues, y compris chemins alternatifs analytics/scoring ML | Tests de suspension ; popularité artistique maintenue |
| Wiki technique | Déplacé dans `docs/archive/wiki`, hors des routes Next.js | Contenu conservé dans la branche ; anciennes URLs absentes du build |
| Abonnements | Core, Premium, Business ; Addons = demande commerciale complémentaire, jamais un quatrième plan | Tests activation, expiration, refus de bascules et autorisations |
| Notifications, suivi de tâches et onboarding | Composants existants réutilisés dans le layout | Compilation ; recette visuelle encore nécessaire |

Les interfaces remplacées se trouvent dans `docs/archive`. Les modèles et services métier utiles restent dans l’application. Les anciennes URLs fusionnées redirigent ; les API de traitement artistique restent disponibles sous contrôle d’abonnement.

## Limites à ne pas présenter comme terminées

- L’ensemble de la plateforme n’est pas certifié prêt à commercialiser. Une recette avec les données réelles, chaque rôle, les intégrations Google et les sources artistiques reste nécessaire.
- Le pipeline réel Celery/Redis n’a pas été testé sur un broker connecté : reprises bornées testées avec panne simulée, sans promesse d’exécution exactement une fois.
- Les performances n’ont pas été mesurées sur les volumes réels. Réduction des appels redondants sur la carte, délais Redis bornés et invalidation par SCAN réalisés ; pas de benchmark de production.
- Les tâches worker, requêtes SQL brutes et intégrations doivent conserver leurs filtres explicites : le filtre ORM de Session HTTP ne constitue pas une politique PostgreSQL RLS.
- Pas de prestataire de paiement d’abonnement intégré ; aucune demande n’est une preuve de paiement. L’activation administrative doit référencer un accord vérifié par l’opérateur.
- Pas de transmission réglementaire de factures électroniques en service. Voir EXPLOITATION.md pour les frontières de l’intégration à prévoir.
- L’historique Alembic complet présente un blocage préexistant sur installation neuve. Sa réparation a été refusée par la revue automatique ; voir MIGRATIONS.md. Les nouvelles migrations sont testées indépendamment sur PostgreSQL.
- Les droits historiques migrés doivent être rapprochés des contrats avant mise en production. Le dépôt ne permet pas de prouver que les anciens packs ont été payés.

## Compléments issus de la validation

- Les protections de login mélangeaient le trafic des pages avec les essais de connexion. Les compartiments de quotas sont séparés, la limite globale est conservée et testée.
- Les en-têtes de proxy non fiables permettaient de choisir une IP ; les exemptions implicites de développeur ont été retirées. La confiance envers les proxys est maintenant explicite.
- PyJWT, déjà utilisé pour SSO et Revolut, est également utilisé pour les tokens de connexion. Le format signé HS256 historique est testé ; expiration, sujet et type sont obligatoires. La dépendance python-jose et son implémentation ECDSA transitive ne sont plus nécessaires.
- La création de dossiers Google Drive utilise les mêmes droits effectifs que les API, même lorsque le plan Business n’a aucun ancien addon. L’intégration bancaire consulte aussi ces droits et reste suspendue.
