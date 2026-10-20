# Radar — lot de refonte à examiner

Cette branche sécurise l’attribution des abonnements, centralise Core/Premium/Business, rationalise les écrans et relie Discovery aux événements et aux projets existants. Elle préserve les comptes, workspaces, modèles et services utiles ; les interfaces retirées sont archivées.

- [Problèmes, inventaire et décisions fonctionnelles](AUDIT.md)
- [Migrations, conservation des droits et blocage historique](MIGRATIONS.md)
- [Tests, résultats et audits de dépendances](VALIDATION.md)
- [Activation, intégrations, facturation électronique et exploitation](EXPLOITATION.md)

**147 tests backend passent ; typage et build frontend ont passé lors du lot précédent.** La réparation de l’historique Alembic a été refusée par la revue automatique et nécessite une autorisation spécifique. Les limites des intégrations externes et de la recette sont détaillées dans les comptes rendus ci-dessous. Aucun déploiement de production ni changement de données de production n’a été effectué.

Audit complémentaire : [API et contrats](API-AUDIT.md).

Parcours navigateur : [validation locale et patch](LOCAL-DEBUG.md).

Collecte artistique : [auditeurs Spotify sans clé API](SPOTIFY-AUDIENCE.md).

Réseaux sociaux : [compteurs Instagram, TikTok et YouTube](SOCIAL-AUDIENCE.md).

Préversion privée : [démarrer Radar dans GitHub Codespaces](CODESPACES.md).

Interface : [thème clair, navigation et parcours modernisés](UI-REFRESH.md).
