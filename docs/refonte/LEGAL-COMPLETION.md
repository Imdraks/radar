# Complément opérationnel France / UE — 13 novembre 2026

Périmètre confirmé : Radar vendu exclusivement aux professionnels. Branche dédiée, aucune production active inspectée, aucun contrat réel signé ou publié pendant ce travail. Ce complément remplace les constats devenus obsolètes de l'audit initial sur l'absence d'archive métier, de preuve contractuelle et d'avoir total. Il ne lève pas les conditions factuelles et opérationnelles de mise en vente.

## Fonctionnement livré

### Documents et acceptations

Six modèles substantiels sont conservés dans `backend/app/resources/legal_templates` : CGV B2B, DPA article 28, conservation, réversibilité, sécurité et prestataires/transferts. Les champs `[[…]]` signalent les informations ou décisions manquantes. Aucun tarif, hébergeur, sous-traitant actif, SLA ou clause de responsabilité n'est inventé. Les textes sont des projets à compléter et revoir, pas des contrats réputés signés.

`scripts/prepare_legal_bundle.py` prépare un dossier JSON hors ligne depuis la configuration publique. Il ne publie rien, conserve `reviewed_for_publication: false` et refuse d'écraser une sortie existante. Exemple :

```sh
python scripts/prepare_legal_bundle.py --version 2026-11-13-draft --output /tmp/radar-legal-draft.json
```

La publication se fait exclusivement par un opérateur de plateforme dans `/admin/legal` ou l'API authentifiée correspondante, après revue réelle. Elle nécessite six textes complets, une version, une référence de revue et une identité publique conforme au hash configuré dans `LEGAL_PUBLISHER_FINGERPRINT`. Une identité différente ou non configurée, des champs non remplis et la modification d'une version existante sont refusés. La validation de l'API vérifie une cohérence technique et la déclaration de l'opérateur ; elle ne vérifie pas l'existence de l'entreprise ou la qualité du conseil juridique.

Les textes publiés sont accessibles et téléchargeables sur `/contracts`, avec leur version et leur SHA-256. Un client habilité accepte une version et la référence d'une offre depuis `/settings/contracts`. La preuve conserve organisation, représentant déclaré, offre, référence commerciale, date serveur et empreinte. Cette acceptation est contractuelle, distincte du consentement aux cookies, et ne confirme aucun paiement.

Une **nouvelle approbation** de plan doit référencer une acceptation correspondante au workspace et au plan. L'opérateur doit toujours rapprocher le bon de commande réel, ses conditions particulières et l'autorisation commerciale ou financière. Le logiciel conserve une référence commerciale ; celle-ci ne remplace pas la conservation de l'offre acceptée et des preuves requises. Les droits déjà attribués aux workspaces ne sont pas supprimés ou requalifiés rétroactivement. Les demandes commerciales restent possibles sans achat automatique ; un refus ne nécessite pas d'acceptation.

### Archive métier et conservation

Un administrateur d'un workspace peut télécharger `/api/v1/privacy/workspace-export?workspace_id=…`, indépendamment du plan. L'interface est dans `/settings/privacy`. L'archive ZIP contient les données JSON attribuées à l'organisation, un annuaire limité aux membres concernés, ses versions contractuelles acceptées, les références externes, un README et un manifeste avec empreintes. Les valeurs financières sont conservées en chaînes décimales.

La liste des tables et champs est revue et figée dans `workspace_export_policy.json`. Tout nouveau modèle ou champ non classé bloque l'export jusqu'à revue. Comptes globaux, mots de passe, secrets de connexion et journaux non attribuables ne sont pas copiés. Les clés JSON et paramètres d'URL identifiés comme identifiants secrets sont masqués. Les dossiers personnels de droits ne deviennent pas des données accessibles à tous les administrateurs du workspace.

Une instruction PostgreSQL fournit les jeux exportés dans un même instantané. Les références interentreprises incohérentes ne sont pas suivies. Une limite de 100 000 lignes ou 30 Mio de données sérialisées produit un refus explicite demandant une restitution assistée ; aucune archive tronquée n'est renvoyée comme complète.

Les originaux Drive et autres binaires externes, les données historiques sans attribution et certaines données globales nécessitent toujours une restitution assistée. Le manifeste l'indique. Cette archive ne constitue donc ni une sauvegarde PostgreSQL ni la preuve d'une réversibilité Data Act exhaustive. Tester un transfert complet incluant les originaux et la réception chez le destinataire avant engagement.

L'inventaire de conservation fournit volumes et ancienneté de certaines catégories. Il ne décide pas qu'un ancien enregistrement est effaçable et n'active aucune purge. Les durées, points de départ, exceptions, sauvegardes et opérations effectives restent à définir et exécuter sous responsabilité identifiée. La page `/retention`, les projets et la procédure opérateur distinguent ces obligations.

### Avoir total et transmission électronique

Une facture émise disposant des preuves d'origine peut recevoir un **avoir total** via son écran. Le document reprend identité, référence/date de l'original, lignes, remise, TVA et montants d'origine. Il est numéroté transactionnellement dans une série `AVO`, comporte un motif et une date d'émission réelle, et peut être téléchargé en PDF. Une seule correction intégrale est autorisée pour cette facture ; la clé d'idempotence protège une reprise après incident.

La facture, sa référence, ses montants et son historique de paiement restent présents. `credited_at` matérialise la correction sans réécrire le statut historique. Un nouveau paiement est bloqué. Les montants à recevoir excluent les factures intégralement couvertes ; les paiements déjà déclarés restent conservés et sont signalés pour rapprochement. Aucun remboursement ou rapprochement bancaire n'est exécuté. Le tableau net ne doit pas être confondu avec un solde bancaire.

**Limites :** avoirs partiels, annulation d'un avoir, remboursement bancaire, réemploi de crédit, régimes fiscaux particuliers et rectification de factures historiques sans preuve ne sont pas automatisés. Un avoir total erroné nécessite un traitement comptable adapté, pas une suppression. Faire valider les documents et leur cycle réel par le conseil comptable.

Un dossier d'échange JSON `radar-invoice-exchange-v1` reprend les données fiscales figées et montants exacts pour préparer le travail avec un prestataire. Le contrôle `/electronic-invoicing` indique les prérequis et conserve `provider_connected: false`, `ready_for_transmission: false`, `not_transmitted`. Ce format Radar n'est pas un UBL, CII ou Factur-X validé. Aucun accusé ou envoi à une plateforme agréée n'est simulé.

## Mise en service à finaliser avec des faits réels

1. Fournir les informations vérifiées de l'éditeur et de l'hébergeur dans `frontend/src/config/legal.json`. L'immatriculation doit correspondre au registre applicable ; aucun RCS ou numéro de TVA ne se déduit du seul siège/SIREN.
2. Compléter et revoir les six modèles avec les conditions particulières, prix réellement validés, responsabilités, instructions, mesures de production et références des annexes. Ne pas publier un projet ou remplacer une décision manquante par une formule vague. Conserver l'offre réellement acceptée.
3. Établir le registre, la liste des prestataires effectivement actifs, leurs rôles, pays, DPA, transferts et données reçues. Le fichier d'inventaire joint recense des connecteurs à qualifier, pas des sous-traitants déjà validés.
4. Définir la conservation par catégorie, les exceptions, les demandes de droits et les opérations de fin de service. Tester sur des données de recette, puis documenter la procédure réelle. Ne supprimer aucune pièce financière ou preuve client par simple ancienneté.
5. Préparer une instance et des sauvegardes de production, recetter TLS, identité, isolation, alertes, restauration, scripts et fournisseurs réels. Aucun ancien serveur ou sauvegarde client n'a été récupéré.
6. Choisir et contractualiser la plateforme agréée adaptée, puis implémenter son adaptateur et recetter formats, identités, taxes, transmission, idempotence, statuts, erreurs et archivage. Le choix du fournisseur et ses habilitations ne peuvent pas être déduits du dépôt.
7. Compléter les analyses d'applicabilité IA/accessibilité/Data Act et les procédures sous responsabilité de l'entreprise. La CI ne constitue pas une certification juridique.

Le contrôle de publication commerciale reste bloquant. Aucun tarif nouveau, prestataire souscrit, facture réelle, acceptation client réelle, paiement, purge, notification réglementaire ou déploiement n'a été effectué.

## Sources complémentaires

Sources de l'audit initial : [LEGAL-FR-EU-AUDIT.md](LEGAL-FR-EU-AUDIT.md).

- [Service Public Entreprendre — facturation et corrections](https://entreprendre.service-public.gouv.fr/vosdroits/F23208).
- [BOFiP — facture rectificative et note d'avoir](https://bofip.impots.gouv.fr/bofip/142-PGP.html/identifiant%3DBOI-TVA-DECLA-30-20-20-20-20220119) : référence explicite à la facture d'origine et mentions applicables ; ne pas généraliser le cas simplifié livré à tous les régimes.
- [DGFiP — traitement d'un avoir sur la TVA](https://www.impots.gouv.fr/professionnel/questions/comment-traiter-une-facture-davoir-sur-ma-declaration-de-tva).
