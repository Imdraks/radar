# Radar — lot de refonte à examiner

Cette branche sécurise l’attribution des abonnements, centralise Core/Premium/Business, rationalise les écrans et relie Discovery aux événements et aux projets existants. Elle préserve les comptes, workspaces, modèles et services utiles ; les interfaces retirées sont archivées.

- [Problèmes, inventaire et décisions fonctionnelles](AUDIT.md)
- [Migrations, conservation des droits et blocage historique](MIGRATIONS.md)
- [Tests, résultats et audits de dépendances](VALIDATION.md)
- [Activation, intégrations, facturation électronique et exploitation](EXPLOITATION.md)

**43 tests backend passent, typage et build frontend passent.** La réparation de l’historique Alembic a été refusée par la revue automatique et nécessite une autorisation spécifique. Les intégrations externes, la recette métier réelle et les alertes de dépendances restantes ne sont pas déclarées résolues. Aucun déploiement ni changement de données de production n’a été effectué.
