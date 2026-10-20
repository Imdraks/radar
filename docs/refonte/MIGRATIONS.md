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

## Blocage historique constaté

Un `alembic upgrade head` sur une base PostgreSQL entièrement neuve échoue avant les nouvelles migrations, dans **032_billing_enhancements** : `devis_template_doc_id` existe déjà depuis 020. Un essai de diagnostic avec garde sur les colonnes a ensuite mis en évidence que `quotes` n’existait pas encore : 032 ne dépend pas de la branche 010_billing. Ces modifications de diagnostic ne sont pas conservées.

La réparation envisagée pour revue est : rendre l’ajout de colonnes de 032 compatible avec celles déjà créées en 020, imposer la création de workspaces avant 010_billing et celle des tables de facturation avant 032, puis vérifier le graphe et les chemins des installations déjà migrées. **Aucun de ces changements historiques n’est inclus.**

La revue automatique a rejeté la réécriture de ces dépendances historiques, jugeant le risque élevé pour les déploiements existants et demandant une autorisation spécifique. Il faut cette autorisation avant de reprendre cette réparation. Les migrations additives et leurs tests restent indépendants de cette décision.


## 050 — Propriété des collectes historiques

Ajout nullable de `collection_runs.workspace_id`, index et clé étrangère. Les anciens runs sont conservés sans attribution inventée ; les API d’agence les masquent tant qu’un rapprochement fiable n’a pas été effectué. Les nouveaux runs portent le workspace authentifié. Les workers refusent les runs non attribués. Downgrade automatique uniquement avant toute attribution ; ensuite, archivage et procédure manuelle nécessaires pour conserver la propriété. Cette migration ne répare ni ne réécrit le graphe historique bloqué.
