# Validation locale et patch — 20 octobre 2026

## Environnement

Backend FastAPI et frontend Next.js exécutés en local dans l’environnement de développement, avec un PostgreSQL jetable, un schéma isolé, Redis local et un compte de test. Aucun compte ni contenu de production n’est utilisé. Les créations métier portent explicitement le préfixe TEST LOCAL.

Le schéma de test est créé depuis les modèles SQLAlchemy : cela permet de vérifier les comportements applicatifs, **pas** de certifier une installation depuis l’historique Alembic. Le blocage historique demeure documenté dans MIGRATIONS.md. La migration additive 050 est testée séparément en montée et descente, avec refus d’un retour arrière qui ferait perdre la propriété enregistrée.

## Couverture

- `scripts/local_site_check.py` : connexion par le vrai formulaire, refus des cookies optionnels, parcours de 52 pages/adresses, observation des erreurs JavaScript, des réponses API et des débordements. Dix contrôles supplémentaires à 768 et 390 pixels sur accueil, projets, événements, Discovery et abonnement. API non simulées ; seul le chargement du service de télémétrie est bloqué dans le navigateur de test.
- `scripts/local_workflow_check.py` : création d’un projet et ouverture de sa fiche ; création d’un événement et apparition dans sa liste ; création d’un client ; création d’un devis brouillon et ouverture de sa fiche. Aucun envoi commercial, paiement ou invitation réelle.
- Suite backend : **69 tests réussis** sur PostgreSQL, couvrant notamment permissions, isolation, abonnements, facturation, événements, erreurs de fournisseurs, JWT et migrations additives.

## Bugs reproduits et patchés

- Administrateur d’agence envoyé à tort vers `/admin` après connexion : redirection fondée sur `is_superuser` et contrôle avant rendu des pages plateforme.
- Sélection initiale du workspace lisant une liste au lieu de `items` dans la réponse : contrat de connexion et de SSO corrigé.
- Ancienne clé `token` utilisée par carte, collecte de leads et calendrier Google : utilisation d’`access_token`.
- Paramètres du workspace utilisant `/workspace/current` et des URL inexistantes : utilisation de `/workspaces/{id}`, des invites et de `/drive/setup`, avec les champs réels de templates et dates de membres. Le propriétaire garde accès aux réglages même sans ligne de membre explicite.
- Réponse PATCH de workspace sans liste de membres : relecture de la fiche après sauvegarde.
- Texte annonçant un email envoyé sans preuve de livraison : confirmation de l’autorisation enregistrée, conforme à l’API.
- Erreurs de chargement des données d’intelligence masquées puis transaction SQL inutilisable : rollback et erreur 503 explicite.

Les autres corrections de sécurité/contrats sont détaillées dans [API-AUDIT.md](API-AUDIT.md).

## Limites

Le premier passage en mode développement a rencontré un délai de compilation sur `/briefs` et une navigation annulée lors de redirections successives. Les redirections et pages concernées sont rejouées avec un build local de production. Une erreur initiale du feed d’intelligence venait aussi d’une table omise dans le montage de la base jetable ; la fixture locale a été complétée, sans modification des données applicatives.

Un passage de liste ne valide pas tous les boutons, variantes de données ou intégrations. Les fiches dynamiques projet/devis sont testées par création réelle ; les autres fiches et actions ont la couverture backend indiquée, sans prétendre à une couverture exhaustive de chaque écran. Google, Spotify/Deezer, mails, banque et paiements nécessitent des environnements fournisseurs dédiés. Les pages plateforme sont vérifiées comme interdites au compte d’agence ; les décisions d’abonnement plateforme sont couvertes par les tests backend.


## Résultat du second passage

Build de production local : **52 pages/adresses et 10 contrôles mobiles réussis**, sans erreur JavaScript, réponse API en erreur ou débordement détecté durant ce passage. Les redirections vers les écrans canoniques et le refus des pages plateforme pour un administrateur d’agence ont été attendus explicitement. Les quatre parcours de création décrits ci-dessus sont passés dans le navigateur avec les API réelles locales. Le dernier ajustement du contrat `items` de sélection initiale est ensuite revérifié avec un rebuild et les parcours de connexion/création. Ces observations restent bornées au jeu de données jetable et à la couverture décrite, sans validation de fournisseurs externes.
