# Radar — parcours et exploitation

## Changements et réutilisation

| Besoin | Réponse |
| --- | --- |
| Parcours fiables | Tests API sur PostgreSQL réel, chaîne de migrations depuis six états et parcours navigateur ; les refus ne sont pas comptés comme des succès métier. |
| Intégrations compréhensibles | `/integrations` expose configuration, autorisations Google du compte, collectes et traitements du workspace courant. Une clé présente n’est jamais présentée comme un fournisseur opérationnel. |
| Recherche transversale | Bouton loupe du header : projets, tâches, livrables, fichiers, clients, artistes et événements, selon les droits effectifs du workspace. Maximum 10 résultats par catégorie. Aucun appel fournisseur ni accès inter-workspace. |
| Structures réutilisables | `/templates`, accessible dans le parcours Projets : modèle de projet ou événement, tâches et livrables, échéances relatives au démarrage. Création atomique dans les modèles métier existants. Les budgets, fichiers, responsables et comptes ne sont pas copiés. |
| Production centralisée | La fiche projet conserve ses onglets existants et ajoute les liens vers l’événement et le client commercial autorisé, ainsi que les validations externes. Les événements utilisent déjà un projet de production unique. |
| Discovery → événement | Le transfert d’artiste existant est conservé, avec permissions Premium et contrôle des deux organisations. La recherche transversale ouvre la fiche Discovery existante. |
| Fiabilité artistique | Les projections existantes conservent sources, dates, données absentes, distinction public/estimé, précision YouTube et refus d’assimiler les fans Deezer aux auditeurs Spotify. Ces garanties restent couvertes par les régressions backend. Aucun algorithme ni statistique fictive n’est ajouté. |
| Validation client | Lien confidentiel en fragment d’URL, révocable et expirant, présenté une seule fois. Le client consulte le livrable et valide ou demande des changements. La réponse met à jour les validations existantes et le statut du livrable. |
| Sauvegarde et surveillance | Scripts et timers systemd ci-dessous : sauvegarde PostgreSQL quotidienne, restauration isolée hebdomadaire, contrôle des services et de la fraîcheur des sauvegardes toutes les 5 minutes. |

## Validation externe : portée et limites

Les jetons sont aléatoires et seul leur SHA-256 est conservé. Ils passent dans le
corps JSON et jamais dans une query string. La page retire le fragment de la barre
d’adresse après lecture. L’API publique ne renvoie ni notes internes ni données
client/workspace ; le lien autorise uniquement ce livrable. Une nouvelle demande
révoque la précédente. Les décisions concurrentes verrouillent le livrable et la
demande ; une seconde décision est refusée. Les espaces suspendus, supprimés ou
sans droits projet ne sont plus accessibles par ces liens.

Le nom du répondant est **déclaratif** : ce mécanisme n’est pas une signature
électronique ni une preuve d’identité. Un changement des métadonnées du livrable
invalide la demande en attente. Un fichier externe modifié au même lien sans
mise à jour dans Radar ne peut pas être détecté : partager une version de fichier
stable pour une validation contractuellement sensible. Le lien ne modifie pas les
permissions Google Drive ; le destinataire doit pouvoir consulter le fichier.
Aucun e-mail n’est envoyé automatiquement à sa création.

La suppression physique d’un projet ou livrable avec historique externe est
refusée avec HTTP 409 ; conserver/archiver le projet. Les demandes expirées et
l’historique ne sont pas purgés automatiquement.

## Migration et données

Migration `066_production_tools` : tables `production_templates` et
`deliverable_reviews`, index workspace et livrable. Aucune donnée préexistante
n’est modifiée. Le downgrade est possible sur tables vides ; une table utilisée
bloque le rollback jusqu’à traitement explicite de son contenu.

Les modèles sont inclus dans l’export de leur workspace. Les jetons de validation
et identités déclaratives sont exclus de l’export automatique pour revue dédiée.
Les contrôles de permissions et d’abonnement restent côté backend.

## Déploiement et automatisation sur le VPS

Après mise à jour de la branche et exécution de `scripts/deploy-client-admin.sh` :

```bash
cd /opt/radar
bash scripts/install-operations.sh
```

L’installation exécute d’abord une vraie sauvegarde et une restauration dans une
base **nouvelle**, nommée aléatoirement `radar_restore_probe_*`. La base en service
n’est jamais restaurée, effacée ou remplacée. La base de test est supprimée en fin
de contrôle, y compris si la restauration échoue. L’installation des timers ne
continue que si ce contrôle réussit. Le rôle PostgreSQL du conteneur doit avoir
le droit de créer/supprimer cette base temporaire. Prévoir de la place et la
charge nécessaire à la copie des données.

Archives custom et manifestes SHA-256 :
`/opt/radar-deployment-backups/scheduled`, répertoire 0700 et fichiers 0600.
Aucune rétention destructrice automatique n’est activée. Les contrôles signalent
un disque avec moins de 15 % libres, des services arrêtés ou unhealthy, un worker
non répondant, une sauvegarde plus ancienne que 36 heures ou l’absence de
restauration vérifiée depuis 8 jours. Consulter :

```bash
sudo systemctl list-timers 'radar-*'
sudo journalctl -u radar-backup -u radar-drill -u radar-monitor --since today
```

Les échecs sont visibles dans systemd/journald. Aucun système d’astreinte externe
n’est configuré automatiquement ; relier ces unités au dispositif de supervision
choisi avant un usage commercial exigeant une alerte hors VPS.

### Copie hors serveur

Une archive sur le VPS ne protège pas d’une perte de ce VPS. Pour activer la copie
SSH/rsync, configurer `/etc/radar-operations.env` (root, 0600) :

```ini
RADAR_BACKUP_REMOTE=utilisateur@serveur-de-sauvegarde:/chemin/prive/
```

Installer rsync et autoriser uniquement cet accès de sauvegarde. Le serveur distant,
son chiffrement au repos, sa rétention et son coût doivent être choisis et vérifiés
par l’opérateur. Aucun fournisseur ou hôte distant n’est inventé. Sans cette valeur,
les journaux annoncent explicitement `offsite_copied: false`.

Ces archives couvrent **PostgreSQL**. Elles ne sont pas une sauvegarde des fichiers
Google Drive, de la configuration `.env`/Nginx ni du volume d’authentification MCP.
Leur conservation sécurisée doit être organisée séparément ; aucun export de
secrets MCP ni arrêt du connecteur n’est effectué par ce chantier.

## Vérifications locales

`test_production_tools.py` couvre l’isolation, les offres, les modèles, les
échéances, les validations, révocations, expirations, versions et la migration.
`workflows_ui_smoke.py` utilise uniquement des fixtures locales pour les écrans.
`check_backup_restore.py` effectue un véritable dump/restore sur PostgreSQL Docker
jetable, vérifie l’empreinte, la conservation des lignes sources et la suppression
de la base de restauration. La CI exécute également ces contrôles.

Les API externes non configurées et l’état du VPS ne sont pas validés par ces
tests. Le centre d’intégrations les distingue explicitement des observations
réelles disponibles.

Résultats de cette livraison : 406 tests backend réussis, build Next.js et typage
réussis ; migrations depuis six états et parcours API sur base migrée réussis ;
quatre files Celery testées avec un vrai Redis/worker ; nouveaux écrans à
1440/390/320 px et régression multi-workspace à 1440/390 px réussis. L’hydratation
d’une session ne remonte plus la page publique de validation après consommation
de son fragment confidentiel.
