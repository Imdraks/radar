# Livraison et restauration de Radar

Ces procédures ne constituent pas une restauration de l’ancien serveur, dont ni disque ni sauvegarde n’ont été fournis. Conserver ses disques et exports avant toute réinstallation. Ne jamais exécuter un restore ou un stamp Alembic aveugle sur une base client.

## Préparation

1. Déployer une copie isolée avec PostgreSQL, Redis et configurations privées propres. Définir les secrets forts, `APP_ENV=production`, `DEBUG=false`, ne jamais activer `TESTING` sur un service client. Le compose de production fixe ces trois variables.
2. Compléter `frontend/src/config/legal.json` avec les vraies informations publiques de l’éditeur et les références HTTPS des documents contractuels. Le flag `commercialReleaseEnabled` reste faux dans le dépôt tant que ces éléments ne sont pas fournis. `python scripts/check_release.py` bloque une publication commerciale incomplète ; `--check-template` ne valide que la structure.
3. Initialiser le premier administrateur hors ligne : `docker compose -f docker-compose.prod.yml run --rm backend python -m app.cli.create_admin --email EMAIL --name NOM`. Le mot de passe est demandé sans être affiché ni placé dans les arguments. L’API publique de setup est désactivée par défaut ; un opérateur peut exceptionnellement configurer un `BOOTSTRAP_TOKEN` et le transmettre via `X-Radar-Bootstrap-Token`. Le vider après usage. Une serrure PostgreSQL sérialise les créations.
4. Préparer TLS et le proxy pour le domaine réellement choisi ; le manifeste livré référence encore radarapp.fr. Vérifier la configuration réseau et les obligations de localisation ; aucune localisation d’hébergement n’est déduite du code.

## Livraison

`RADAR_DEPLOY_DIR`, `RADAR_BACKUP_DIR`, `RADAR_DEPLOY_LOG` et `RADAR_DEPLOY_REF` permettent de choisir les chemins et la référence Git approuvée ; les défauts restent `/opt/radar`, `/opt/backups/radar` et `main`. Le script ne pousse jamais de code. Utiliser une référence revue, pas une branche mouvante non contrôlée.

`deploy.sh --full` et `--quick` réalisent tous deux les étapes indispensables : configuration vérifiée, PostgreSQL/Redis démarrés, sauvegarde si base non vide, checkout propre, contrôle commercial, images reconstruites, migration via la nouvelle image, services et readiness. Aucun stash automatique, aucune copie d’exemple de secrets, aucun faux succès après un processus échoué. Les ports internes sont vérifiés dans les conteneurs, pas sur des ports hôte non publiés.

La readiness contrôle base, révision Alembic, historique artiste, Redis, frontend et consommateurs de toutes les files routées. Elle ne prouve pas qu’un fournisseur externe répond correctement. Configurer également une vérification HTTPS extérieure et des alertes d’exploitation.

## Sauvegarde et restauration

`deploy.sh --backup` produit une archive PostgreSQL custom temporaire, refuse un dump échoué/invalide, puis crée archive finale, SHA-256, commit et révisions de schéma. Répertoire 0700 et fichiers privés. Les anciens exports ne sont jamais purgés automatiquement : définir une rétention, une copie hors machine et le chiffrement de stockage/transfert avec l’hébergeur. Le script n’est pas une solution de sauvegarde hors site.

Avant de toucher une base existante :

1. Arrêter ou maîtriser les écritures selon la procédure d’exploitation ; produire l’archive et vérifier son SHA-256 et `pg_restore --list`.
2. Créer **une nouvelle base isolée** avec une version PostgreSQL compatible ; restaurer avec `pg_restore --exit-on-error --no-owner` sous un compte adapté. Ne pas utiliser `--clean` contre une base client.
3. Comparer comptes, workspaces/membres, références/totaux des documents, projets, événements, artistes et révisions. Vérifier les fichiers/objets externes séparément : `pg_dump` ne sauvegarde pas Google Drive ni le stockage tiers.
4. Tester les migrations sur cette restauration, conserver un rapprochement écrit et vérifier les accès entre agences. Fixer RPO/RTO et rejouer périodiquement cet exercice.
5. Choisir les images du commit compatible avec le schéma restauré, effectuer une recette puis une bascule contrôlée. Éviter d’avoir deux serveurs qui écrivent et exécutent les mêmes jobs.

`--rollback` refuse désormais un retour automatique fondé sur un simple checkout : celui-ci ne restaure ni le schéma ni les images. Les downgrades destructeurs sont explicitement refusés ou conservateurs ; voir MIGRATIONS.md.

## Intégrations et offre

Les quatre files `celery,dossier_builder_gpt,web_enrichment,ingestion_standard` ont des consommateurs explicites. CI exécute des échanges réels avec un broker jetable ; ce ne sont pas des appels aux API clients.

YouTube/OAuth/messagerie et autres intégrations nécessitent vrais comptes et clés de recette dans le gestionnaire de secrets. Aucun paiement ni succès fournisseur n’est simulé en production. L’enregistrement de paiements reste une déclaration humaine. Le connecteur de facturation électronique est une interface de transport non configurée, sans transmission réelle ; ne pas annoncer une conformité réglementaire à partir d’un PDF.

Le suivi navigateur est désactivé si `NEXT_PUBLIC_GA_ID` n’est pas configuré à la construction. Si activé, son script ne charge qu’après acceptation analytics ; GTM et son iframe ont été retirés. Le refus initial et le retrait ne doivent pas déclencher de requêtes analytiques. Les tokens SSE passent par Authorization et les WebSockets par sous-protocoles, jamais dans la query string ; le proxy ne journalise plus les arguments ni les referers.
