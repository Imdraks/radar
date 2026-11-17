# Corrections de l’audit commercial — 13 novembre 2026

Ce lot répare les défauts logiciels vérifiables du rapport du 13 novembre. Il ne récupère pas l’ancien serveur et ne constitue pas une validation juridique ou fournisseur.

| Audit | Changement | Limite restante |
|---|---|---|
| A01 migrations | Dépendances historiques explicites, colonnes communes non recréées, migrations 051/052, test de six parcours et comparaison modèles/schéma | Anciennes bases réelles inconnues ; tester leur restauration avant reprise |
| A02 intégrité financière | Actions centralisées avec verrou de ligne ; facture émise figée, aucun retour brouillon/suppression, paiement brouillon/annulé rejeté ; identité photographiée, champs d’émission vérifiés ; paiements audités et cumul monotone | Rectification des factures émises à gérer par un mécanisme d’avoir adapté, non implémenté ici ; anciens originaux à conserver |
| A03 exploitation | Erreurs propagées, archives custom atomiques et vérifiées, readiness interne, refus du faux rollback | Sauvegarde hors site/chiffrement/rétention, alertes et bascule de production à configurer |
| A04 Celery | Quatre files consommées, Celery/Kombu/Redis compatibles et épinglés, test réel broker/worker en CI | Les échanges de test ne valident pas les fournisseurs externes |
| A05 premier admin | Setup public fermé par défaut, secret d’opérateur optionnel, verrou PostgreSQL, CLI hors ligne | Créer le vrai compte administrateur avant exposition |
| A06 jetons/logs | SSE par Authorization, WS par sous-protocoles, diffusion limitée au workspace, revalidation heartbeat, caches locaux de notifications supprimés, arguments/résultats de tâches non imprimés | Manager WS encore local à chaque processus ; pas de diffusion interprocessus annoncée |
| A07 dépendances | Node 24, Zod/resolver/follow-redirects corrigés ; audit npm en CI ; dépendances Python installées en environnement vierge | Audits datés, à maintenir ; audit des images système et exploitation à compléter |
| A08 identité/consentement | Scripts Google conditionnés à un choix explicite ; GTM retiré, refus par défaut et préférences accessibles ; identité/hébergement configurables, lancement commercial bloqué si incomplets | Les informations réelles et documents de l’éditeur n’ont pas été fournis |
| A09 provenance | Sources du snapshot issues des observations disponibles ; suppression des scores qualité inventés et des zéros absents ; catalogue statique exclu des scans réels | Prédictions/cachets heuristiques, non calibrés sur données représentatives ; aucun chiffre de précision inventé |
| A10 e-facturation | Contrat de transport spécialisé, capacité API explicite indisponible, avertissement de facturation et paiement manuel | Choix/contrat/identifiants d’une plateforme agréée et recette réels nécessaires ; aucun faux connecteur opérationnel |
| A11 faux signaux/501 | Badges/comptages factices supprimés de leads ; endpoints legacy 501 retirés du contrat OpenAPI | Code historique conservé ; API Discovery principale conservée |

La configuration publique est `frontend/src/config/legal.json`. Elle contient des champs vides et `commercialReleaseEnabled:false` tant que l’identité, l’hébergement et les documents ne sont pas connus ; elle n’invente ni société ni hébergeur. `scripts/check_release.py` interdit une publication commerciale prématurée sans empêcher les tests/recettes locales.

Validation et reprise : voir RELEASE-RECOVERY.md et les résultats de ce lot dans VALIDATION.md. Aucun prix n’a été changé, aucune fonctionnalité bancaire réactivée, aucune donnée client supprimée, aucun push sur main et aucun déploiement en production effectué.
