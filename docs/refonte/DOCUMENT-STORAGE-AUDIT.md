# Audit du stockage documentaire Radar — 20 novembre 2026

## Périmètre et conclusion

Audit du dépôt : routes d’upload, services Drive, génération de PDF, modèles
PostgreSQL, ingestion, sauvegardes et configurations Nginx fournies. Ce contrôle
ne prouve pas le contenu du disque, des volumes, des caches ou de la base du VPS.
Les configurations `compose.server.yml` et Nginx effectivement utilisées sur ce
serveur doivent être confrontées à ces constats.

Les fichiers de production clients sont organisés dans Google Drive. Radar
conserve néanmoins des données clients et, pour certains modules, du contenu
documentaire dans PostgreSQL. La formule « aucun fichier client durable sur le
serveur applicatif » doit rester distincte de « aucune donnée client hébergée ».
Une politique « uniquement Drive » pour les fichiers ne remplace pas la protection
de la base, des accès Google et des sauvegardes.

## Cartographie vérifiée dans le code

| Objet | Stockage / traitement | Preuve |
| --- | --- | --- |
| Fichiers liés aux projets et livrables | URL et identifiants Drive en base ; fichiers chez le fournisseur | `backend/app/db/models/agency.py`, modèles Asset/Deliverable/Project |
| Upload client vers Drive | Le fichier passe par le backend ; lecture intégrale en mémoire puis appel Google multipart/resumable ; aucun archivage binaire durable trouvé dans cette route | `backend/app/api/google_drive.py`, `upload_file_to_drive` ; `backend/app/services/google_workspace.py`, `upload_file` |
| PDF devis et factures des agences | Génération en `BytesIO`, réponse de téléchargement ou envoi à Drive ; données sources et lignes conservées en base | `backend/app/api/billing.py`, routes `/pdf` et `/pdf/drive` ; `backend/app/db/models/billing.py` |
| Factures émises | Snapshot JSON persistant pour conserver les informations d’émission | `Invoice.issued_snapshot` dans `backend/app/db/models/billing.py` |
| Contrats gérés par le super-admin | PDF original dans PostgreSQL (`LargeBinary`), empreinte et métadonnées ; routes protégées par super-admin explicite | `ExternalClientContract.document`, `backend/app/api/platform_sales.py` |
| Devis Radar vers ses entreprises clientes | Émetteur, acheteur et lignes en base ; génération PDF | `PlatformQuote` dans `backend/app/db/models/platform_sales.py` |
| Photos de profil chargées par les utilisateurs | Miniature JPEG en PostgreSQL, jusqu’à 64 Kio ; concerne les comptes utilisateurs, pas seulement les super-admins | `User.avatar_image`, `backend/app/services/profile_avatar.py`, `/auth/me/avatar` |
| Dossiers/collectes/enrichissements | Texte et HTML bruts ou extraits, preuves et métadonnées conservés en base | `source_documents.raw_text/raw_html`, `source_documents_v2`, `Document.full_content` ; workers `collection_pipeline.py`, `collection_tasks.py`, service `web_enrichment.py` |
| Validations externes | Nom/lien du livrable, identité déclarée et retour ; pas de copie du fichier dans ce mécanisme | `DeliverableReview.snapshot/feedback`, `backend/app/api/production_tools.py` |
| Plans de production | Intitulés et échéances des tâches/livrables dans la définition du modèle | `ProductionTemplate.definition` |
| Accès Google | Jetons OAuth actuellement conservés dans Redis ; leur protection reste nécessaire même si les fichiers sont chez Google | `backend/app/core/integration_oauth.py`, `save_tokens` |
| Sauvegardes PostgreSQL | Incluent aussi les contenus et snapshots ci-dessus ; archives custom non chiffrées par l’application | `scripts/operations.py`, `deploy.sh` |

Les contenus issus de la collecte ne sont pas assimilés automatiquement aux
fichiers de production des agences : leur origine effective dépend des sources
et fonctions activées. L’inventaire agrégé permet de vérifier leur présence,
sans ouvrir les documents. Certains parcours d’extraction/analyse utilisent le
texte disponible avec un fournisseur IA configuré ; ils ne permettent pas de
promettre que tout traitement documentaire reste exclusivement chez Google.

## Fichiers temporaires et transit

L’upload `multipart/form-data` utilise UploadFile. La version Starlette installée
emploie `SpooledTemporaryFile` : au-delà de son seuil de 1 Mio, le corps peut être
placé temporairement sur disque avant l’appel à Google. Nginx peut également
bufferiser le corps des requêtes. Le dépôt annonce un buffer de 16 Kio dans
`docker/nginx/nginx.prod.conf`. Il n’est donc pas possible d’affirmer « aucun
passage sur disque » avec ce proxy d’upload.

Le framework ferme normalement les fichiers de formulaire à la fin de la
requête. Ce comportement ne prouve pas l’absence de résidus d’anciennes versions,
de journaux personnalisés, de dumps, d’exports manuels ou de volumes sur le VPS.
Aucun effacement de données ou de fichier n’a été exécuté pendant cet audit.

## Points relevés à traiter / confirmer

1. Le proxy d’upload lit tout le fichier avant sa validation de taille (50 Mio).
   Borner la lecture et vérifier le nettoyage sur tous les chemins d’échec serait
   un renforcement utile. La configuration Nginx du dépôt limite le corps à 10 Mio :
   cette divergence nécessite de vérifier le proxy actif, notamment pour les gros fichiers.
2. Les erreurs Drive réutilisent des messages fournisseur et une exception générique
   peut renvoyer du détail technique. Uniformiser leur projection publique sans
   perdre les diagnostics internes.
3. Aucun mécanisme ne garantit à lui seul qu’un upload personnel accessible avec
   le compte Google courant est rangé dans le bon dossier métier. Vérifier les
   permissions Drive et l’association du dossier au workspace lors de la recette.
4. Si l’exigence est stricte « pas de fichier temporaire client côté Radar », prévoir
   un upload navigateur → Drive avec autorisation adaptée, ou un pipeline de
   streaming contrôlé ; augmenter seulement le seuil RAM n’est pas une garantie.
5. Chiffrer les sauvegardes, protéger les jetons OAuth, vérifier le chiffrement disque,
   les accès Redis/PostgreSQL et organiser la copie hors VPS restent nécessaires.
6. Les contenus historiques d’ingestion, les snapshots de factures et les pièces
   super-admin exigent des règles de conservation distinctes. Ne rien purger sans
   examiner les dépendances et les obligations de conservation.

## Vérification de la base réellement déployée, sans lecture de contenu

`scripts/storage_inventory.py` utilise les paramètres déjà chargés par le backend.
Il ouvre une transaction PostgreSQL **READ ONLY**, borne chaque requête à 10 s et
ne retourne que table, colonne et nombre de valeurs non nulles. Il ne renvoie ni
contenu de document, ni nom de client, ni adresse, ni clé, ni identifiant de ligne.
Une valeur non nulle peut être vide ; un décompte ne qualifie pas le document.
Une table absente/non visible est signalée comme telle, jamais comme vide.

Sur le VPS, après récupération de la branche d’audit :

```bash
cd /opt/radar
sudo git fetch origin
sudo git show origin/audit/document-storage:scripts/storage_inventory.py |
  sudo docker exec -i radar-backend-1 python -
```

Utiliser `set -o pipefail` dans le shell pour faire remonter un échec de récupération
du script. Aucun redéploiement, migration, suppression ou `git reset` n’est requis.
La sortie agrégée peut être examinée sans transmettre de documents ou secrets.

Les contrôles disque/volumes/sauvegardes et la configuration active du proxy
restent à effectuer sur le VPS. Ne pas joindre de `.env`, jetons ou fichiers
clients à une demande d’audit.
