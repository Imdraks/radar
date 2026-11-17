# Migrations et retour arrière

Aucune migration n’a été appliquée à la production. Tester une copie isolée, sauvegarder et rapprocher les contrats avant toute mise en service.

## Nouvelles révisions

1. **046_product_subscriptions** : photographie des anciens noms dans `subscription_legacy_snapshot`, catalogue officiel, demandes et décisions d’activation. Les packs, addons, comptes et limites de sièges existants ne sont pas supprimés. Les nouveaux workspaces démarrent sur Core.
2. **047_production_events** : événements de production, liens vers projets et artistes, dépenses.
3. **048_tag_associations** : table `custom_opportunity_tags`, distincte du dictionnaire historique. Copie seulement si l’ancienne table comporte les colonnes d’association attendues et si les objets référencés existent. L’ancienne table reste intacte.
4. **049_billing_numbering** : compteurs initialisés à partir des références existantes, unicité `(workspace_id, reference)`. Aucun document n’est renuméroté.

## Compatibilité des abonnements

La migration conserve les droits commerciaux auparavant activés, sans prélèvement ni facture :

- Ancien Premium, addon `radar_business`, pack clients ou leads → Business.
- Ancien Standard dépourvu de ces droits → Premium.
- Ancien Mini dépourvu de ces droits → Core.

Le nom Premium change donc de périmètre. La photographie est impérative pour distinguer l’ancien du nouveau. Ne pas déployer le code avec l’ancien état de schéma. Tous les anciens workspaces dont les packs par défaut incluent les clients seront proposés en Business : c’est une conservation des accès, pas une validation de leurs contrats ni de leurs paiements. Contrôler la photographie en recette avant toute attribution réelle.

Les champs legacy restent stockés pour l’historique et les intégrations ; ils n’accordent plus de droits supplémentaires aux plans officiels. Les activations ultérieures passent par une demande puis une décision de superuser référencée. Les addons sur mesure ne sont jamais activés par un simple booléen.

## Réversibilité

- 046 restaure les noms photographiés si aucune demande n’a été enregistrée et si les plans n’ont pas divergé ; sinon refus explicite pour préserver les décisions.
- 047 refuse de détruire des événements existants au downgrade.
- 048 refuse de supprimer des associations modernes non vides.
- 049 refuse le retour à l’unicité globale si des références identiques existent entre entreprises, ou si des compteurs doivent être conservés. Il faut alors un plan manuel avec archive, sans renumérotation de facture.

Ces garde-fous sont intentionnels : un downgrade ne doit pas effacer silencieusement les données métier ni les preuves d’autorisation. Les tests exécutent les upgrades et retours arrière possibles sur une base jetable.

## Réparation du blocage historique — 13 novembre 2026

La demande de correction de l’audit autorise désormais la réparation sur la branche de travail. Aucun schéma de production n’a été modifié. Les identifiants et parents `down_revision` restent identiques :

- 010 déclare une dépendance sur `020_workspace_inbox`, qui crée workspaces avant ses clés étrangères.
- 032 dépend de 010 ; ses ajouts de colonnes sont conditionnels, car 020 possède déjà certaines colonnes. Aucune valeur existante n’est écrasée.
- Le graphe est acyclique, avec une seule tête. Six parcours — vide, 020 inbox, 010 billing, 032, 043 et 050 — sont testés dans de nouvelles bases avec conservation d’un propriétaire, workspace et identifiant de template. Un second upgrade est sans effet.
- Le downgrade de 032 refuse de retirer les colonnes communes à 020 : une restauration vérifiée et revue est nécessaire pour revenir derrière cette étape sans perdre de données.

Ces tests couvrent des états reconstruits depuis les migrations. Ils ne garantissent pas l’état d’un ancien serveur modifié manuellement ; restaurer et examiner sa sauvegarde avant toute reprise. Ne pas changer arbitrairement les révisions enregistrées avec `stamp`.

## 050 — Propriété des collectes historiques

Ajout nullable de `collection_runs.workspace_id`, index et clé étrangère. Les anciens runs sont conservés sans attribution inventée ; les API d’agence les masquent tant qu’un rapprochement fiable n’a pas été effectué. Les nouveaux runs portent le workspace authentifié. Les workers refusent les runs non attribués. Downgrade automatique uniquement avant toute attribution ; ensuite, archivage et procédure manuelle nécessaires pour conserver la propriété. Cette migration ne répare ni ne réécrit le graphe historique bloqué.

## 051 — Photographie des factures émises

Ajoute `invoices.issued_at` et `issued_snapshot`, nullables. Les nouveaux documents photographient émetteur et client au passage en SENT. Les anciens documents restent présents sans photographie inventée ; leur régénération est refusée, leur original reste la référence. Le downgrade refuse de supprimer une preuve d’émission existante.

## 052 — Alignement du schéma historique

Ajoute si absents `collection_runs.brief_id` (UUID nullable, lien vers briefs) et `comments.is_internal` (booléen, true pour préserver la confidentialité historique). Aucun lien historique n’est deviné. Les champs sont conservés au downgrade ; celui-ci refuse si des liens ou visibilités personnalisées devraient être archivés. Ce retour est volontairement non destructeur et ne reconstitue donc pas à l’identique l’ancien schéma physique.

## 053 — Dossiers de demandes de droits

Ajoute `privacy_requests`, ses index et les liens nullables utilisateur/workspace (`ON DELETE SET NULL`). Conserve type, portée, échéances, réponse et journal de décision. Aucun compte, fichier ou document existant n’est supprimé. Le downgrade refuse dès qu’un dossier existe ; prévoir archivage validé et retour manuel plutôt que détruire les demandes.

## 054 — Mentions déclarées des factures

Ajoute `invoices.legal_details` JSON nullable. Les anciennes mentions ne sont pas inventées. Les brouillons incomplets doivent être complétés avant émission ; les factures émises restent figées. Le downgrade refuse si une valeur existe afin de préserver ces informations.

Le changement de numérotation relève du code : les nouveaux brouillons ont une référence provisoire ; le numéro final et la date réelle sont alloués à l’émission. Un ancien brouillon recevra un numéro définitif selon cette règle, sans renuméroter les documents déjà émis. Aucun numéro ancien n’est recyclé. Les dates et les mentions fiscales doivent être vérifiées en recette ; conserver les originaux des factures historiques dépourvues de photographie.

## 055 — Versions et preuves contractuelles

Ajoute `legal_bundles`, `legal_acceptances` et `subscription_requests.contract_acceptance_id` nullable. Aucun consentement, contrat ou paiement historique n'est inventé. Les anciennes attributions restent présentes ; toute nouvelle décision d'approbation doit rattacher une acceptation valable pour ce workspace et ce plan. Les textes publiés sont immuables par les API ; une nouvelle version est nécessaire pour les modifier. Le downgrade refuse dès qu'une publication existe afin de conserver les preuves.

## 056 — Avoirs totaux

Ajoute `credit_notes` et `invoices.credited_at` nullable. La facture d'origine et ses paiements restent conservés ; les documents déjà présents ne sont pas convertis en avoirs. Un avoir total reprend les montants et mentions figés, reçoit une série transactionnelle AVO et bloque les nouveaux paiements sur l'original. Aucun remboursement automatique ni suppression n'est effectué. Downgrade refusé dès qu'un avoir ou marquage existe ; prévoir archivage et plan comptable de retour manuel.
