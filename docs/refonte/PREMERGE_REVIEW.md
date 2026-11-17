# Corrections des observations de revue avant intégration dans main

Les callbacks Google Calendar (`/api/v1/calendar/google/callback`) et Drive
(`/api/v1/drive/auth/callback`) sont enregistrés séparément des endpoints interactifs.
Ils ne demandent pas de Bearer : le retour de Google n’en fournit pas. Les autres
endpoints conservent leurs dépendances de workspace, permissions et authentification.

Le state opaque est créé uniquement depuis une session authentifiée et un workspace
accessible. Il est partagé dans Redis avec une durée de dix minutes et consommé
atomiquement via GETDEL. Il est lié à l’utilisateur, au workspace, à la session,
à la version de sécurité et au type d’intégration. Le callback refuse un state
absent, expiré, utilisé ou destiné à une autre intégration. Il revérifie compte,
session et appartenance au workspace avant et après l’échange externe. Une erreur
Redis est explicite et aucune connexion n’est annoncée sans enregistrement des
autorisations. Les erreurs fournisseurs ne sont pas renvoyées dans les URLs.
Les demandes de connexion Google en cours avant ce changement devront être relancées.

La suppression directe d’un workspace est limitée aux espaces sans données métier.
Les références déclarées dans les modèles sont vérifiées dans le schéma courant,
sans supposer `public`. Les demandes d’abonnement, compteurs de facturation,
événements, factures et autres données métier entraînent une réponse 409 et sont
conservés. Le propriétaire est orienté vers Données et droits pour la résiliation
ou une suppression contrôlée selon la rétention. Les membres et invitations d’un
espace vide sont retirés dans la même transaction ; toute contrainte restante
annule la transaction et produit une réponse explicite, au lieu d’un HTTP 500.
Aucune donnée de production n’a été supprimée pour les tests de cette correction.

Aucune migration de schéma et aucun secret nouveau ne sont nécessaires. Les tests
emploient des réponses Google simulées et une base PostgreSQL jetable ; ils ne
prétendent pas valider les autorisations réelles du projet Google Cloud du VPS.
