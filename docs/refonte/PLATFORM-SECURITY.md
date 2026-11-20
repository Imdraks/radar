# Durcissement Radar — 20 novembre 2026

## Résultat et périmètre

Correctif sur `security/platform-hardening`, empilé sur `audit/document-storage`.
Il renforce les accès navigateur, les contenus HTML, le transit des uploads,
les secrets OAuth et les données binaires locales, ainsi que les sauvegardes.
Il conserve les API natives, le connecteur MCP et les fichiers Drive.
Aucune donnée de production n’a été supprimée ; aucun accès SSH au VPS n’a été utilisé.
Le contrôle du serveur effectivement déployé reste nécessaire.

### Sessions et copie de cookies

Les JWT du navigateur passent dans des cookies HttpOnly, Secure et host-only
(`__Host-` en production, SameSite=Lax). Le stockage local ne conserve que des
marqueurs et un identifiant de session non secret. Une clé ECDSA P-256 privée
non exportable par WebCrypto est conservée dans IndexedDB ; sa partie publique
est liée à la session PostgreSQL. Les requêtes signent l’identifiant de session,
la méthode, la cible exacte avec sa query string, l’heure et un nonce unique.
Redis refuse les preuves rejouées ; une panne Redis ferme l’accès protégé avec
une indisponibilité explicite, sans désactiver la vérification.

Les cookies copiés dans un autre navigateur, même avec le même User-Agent et le
même localStorage, ne suffisent plus. Le bearer d’une session déjà liée exige
également la preuve ; le changer d’en-tête ne contourne pas la protection.
La connexion WebSocket utilise un ticket à usage unique de 30 secondes, lié au
workspace et à la session. Les opérations cookie sensibles vérifient aussi Origin.
Le renouvellement automatique signe ses requêtes, y compris après expiration
ou rejet du cookie d’accès. Les marqueurs comportent le sid et les réponses
Axios obsolètes sont écartées après un changement de session.

Ce n’est **pas une attestation matérielle** : une copie complète du profil ou
une compromission de l’OS peut encore permettre d’utiliser la clé. Un script
malveillant exécuté dans l’origine peut agir avec la session ; le nettoyage
HTML réduit des chemins XSS connus sans prouver l’absence de toute XSS.
Les clés d’accès/FIDO2 et la réauthentification restent utiles pour les actions
sensibles. Le cookie « autoriser 30 jours » ne connecte jamais seul : il garde
le fonctionnement existant de dispense A2F après saisie du mot de passe.

Les anciennes sessions bearer natives restent compatibles et révocables.
Un navigateur utilisant encore des JWT en localStorage les échange contre les
cookies lors de sa prochaine identification réussie. Cette migration n’annule
pas rétroactivement un ancien jeton volé avant sa liaison ou son expiration.
Révoquer les sessions suspectes depuis les paramètres, et les identifiants
provisoires précédemment partagés, reste nécessaire.

### Chiffrement et données conservées

- Les jetons Google en cache Redis sont enveloppés avec Fernet et liés à leur
  propriétaire de cache ; une permutation de valeur entre utilisateurs est refusée.
- Les champs OAuth Account sont chiffrés à l’écriture et lors de la migration.
- Les photos de profil et les PDF contractuels super-admin sont chiffrés avec
  AES-256-GCM et des contextes distincts. Les téléchargements conservent les mêmes
  octets d’origine après déchiffrement, donc les empreintes restent valables.
- `DATA_ENCRYPTION_KEY` devient la clé dédiée. Les anciennes valeurs restent
  lisibles avec la clé historique issue de SECRET_KEY ; les clés de données
  précédentes peuvent être renseignées dans `DATA_ENCRYPTION_PREVIOUS_KEYS`.
- La commande `python -m app.core.credential_cache` transforme explicitement
  les anciennes valeurs OAuth, binaires et champs Fernet MFA/IBAN/banque en
  lots compatibles. Un arrêt partiel peut être repris avec les mêmes clés.

Ce correctif ne chiffre pas chaque colonne de PostgreSQL : noms, projets,
contacts, montants, snapshots, textes collectés et métadonnées restent nécessaires
au fonctionnement applicatif. Il ne configure pas le chiffrement disque du VPS.
Les temporaires multipart/Nginx et le dump de travail existent pendant les
traitements ; un arrêt brutal peut laisser des résidus. Les données Drive et
les services tiers gardent leurs propres protections et politiques de conservation.
Une copie de la base **et des clés du serveur** peut permettre le déchiffrement.

### Autres protections

HTML riche centralisé dans un composant DOMPurify avec liste de balises/attributs
permise, sans scripts, images, formulaires ni styles utilisateurs. Six anciens
points d’insertion ont été remplacés. Next.js passe en 15.5.29. Le CSP de
production ne comporte plus unsafe-eval, mais garde unsafe-inline pour le Next
actuel : il n’est pas présenté comme un CSP strict à nonce.

L’upload Drive lit au maximum 50 Mio + 1 octet, ferme le fichier même en erreur,
préserve les refus de validation et masque les erreurs fournisseur. Les URL
d’upload Google sont contrôlées avant d’y envoyer jetons et fichiers. La limite
ASGI totale est de 52 Mio pour le multipart ; le modèle Nginx est aligné sur 52m.
Le proxy Nginx réellement installé sur le VPS doit être vérifié séparément.

Les réponses API sont non stockables, les configurations critiques de production
(debug, HTTPS, clés courtes) sont rejetées, l’OpenAPI est désactivé en production,
et les exceptions globales n’impriment plus les paramètres SQL ni leur message
potentiellement sensible. L’overlay Docker retire les capacités Linux et interdit
la prise de nouveaux privilèges aux services backend, worker et scheduler.
Il doit rester inclus lors des futures recréations de ces services.

## Avant de déployer : destinataire des sauvegardes

Les nouvelles sauvegardes PostgreSQL sont des enveloppes CMS AES-256-GCM.
Le VPS n’a besoin que du **certificat public** ; garder la clé privée et sa
phrase de passe hors du serveur, sauvegardées dans un lieu fiable.
Les anciennes archives non chiffrées ne sont ni supprimées ni converties
silencieusement. Les inventorier et les traiter après une restauration vérifiée.

Sur un poste de confiance équipé d’OpenSSL (par exemple Linux ou WSL), créer
une clé privée chiffrée et le certificat public ; OpenSSL demandera une phrase
de passe à conserver dans votre gestionnaire de secrets :

```bash
umask 077
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -aes-256-cbc -out radar-backup-private.pem
openssl req -new -x509 -sha256 -days 3650 -key radar-backup-private.pem -out radar-backup-recipient.pem -subj '/CN=Radar backup recovery/'
scp radar-backup-recipient.pem ubuntu@51.255.166.15:/tmp/radar-backup-recipient.pem
ssh ubuntu@51.255.166.15 'sudo install -d -m 700 /etc/radar && sudo install -m 600 /tmp/radar-backup-recipient.pem /etc/radar/backup-recipient.pem && rm /tmp/radar-backup-recipient.pem'
```

Ne pas copier `radar-backup-private.pem` sur le VPS. Conserver également les
clés applicatives historiques et la nouvelle DATA_ENCRYPTION_KEY dans un coffre
séparé : une sauvegarde PostgreSQL ne contient pas les secrets de configuration
nécessaires au déchiffrement des champs. La sauvegarde doit être copiée hors VPS
pour résister à la perte du disque ; `RADAR_BACKUP_REMOTE` est prévu à cet effet.

## Déploiement sur le VPS

Cette branche inclut les changements de ses branches parentes ; elle doit être
revue avant fusion. Ne pas utiliser git reset --hard ni git clean pour effacer
les adaptations locales du connecteur et les fichiers Compose du VPS.

```bash
ssh ubuntu@51.255.166.15
cd /opt/radar
sudo git fetch origin security/platform-hardening
sudo git switch security/platform-hardening
sudo git pull --ff-only origin security/platform-hardening
sudo bash scripts/deploy-client-admin.sh
sudo python3 scripts/check_vps_security.py
```

Si Git signale un conflit local, arrêter et examiner la différence avant de
la sauvegarder/réconcilier. Le script prépare uniquement une clé de données
manquante dans .env, sans remplacer SECRET_KEY/JWT_SECRET_KEY, puis vérifie
les prérequis. Une clé historique faible demande un plan de rotation spécifique,
pas un remplacement improvisé. Le script crée une sauvegarde chiffrée, conserve
les références des anciennes images, compile, applique Alembic, démarre les
services applicatifs et migre les champs chiffrés. PostgreSQL, Redis et le
connecteur MCP ne sont pas recréés par cette commande.

La migration additive `067_browser_key_binding` ajoute la clé publique aux
sessions. Son downgrade refuse de supprimer la protection tant que des sessions
liées non révoquées existent. Après conversion des champs et binaires, un retour
à une ancienne image ne comprenant pas le nouveau chiffrement **n’est pas un
rollback sûr**. Privilégier une correction compatible, ou une restauration
coordonnée de l’archive antérieure avec les clés, après arrêt contrôlé des
écritures et acceptation des conséquences sur les données plus récentes.
Ne jamais restaurer automatiquement la base de production pour un échec de build.

## Restauration et vérifications

Déchiffrer une copie d’archive sur un poste/serveur de restauration de confiance :

```bash
umask 077
openssl cms -decrypt -binary -inform DER -in radar-ARCHIVE.dump.cms -recip radar-backup-recipient.pem -inkey radar-backup-private.pem -out radar-restored.dump
pg_restore --list radar-restored.dump
```

Vérifier l’empreinte SHA-256 du fichier chiffré contre le manifeste avant de
restaurer. Effectuer d’abord la restauration dans une **base isolée**, jamais
sur la production. Le déchiffrement demande la phrase de passe privée.
Le drill `operations.py drill` restaure le dump de travail dans une base
jetable avant de sceller l’archive ; le test automatique vérifie aussi le
chemin archive chiffrée → déchiffrement → restauration et refuse une altération.

Vérifier sur le VPS : HTTPS, connexion par mot de passe/Google/A2F/passkey,
renouvellement, déconnexion/révocation, choix de workspace, photos/PDF historiques,
Drive, commandes super-admin, workers et cache Redis. Le contrôle VPS est en
lecture seule : il ne modifie ni SSH ni le pare-feu. Ne désactiver les accès
par mot de passe SSH qu’après avoir éprouvé un accès par clé de secours.
L’ouverture des ports depuis Internet, les règles Cloudflare/OVH, le disque,
les sauvegardes hors site et les alertes restent à confirmer en environnement réel.

## Tests reproductibles

Les tests backend couvrent liaison/refus des clés étrangères, origine, nonce,
rejeu, refresh/logout, ticket WebSocket, chiffrement et compatibilité de lecture,
limites d’upload et isolation existante. Le test `security_browser_smoke.py`
utilise un vrai Chromium, Next, FastAPI, PostgreSQL et Redis isolés : il vérifie
la copie des cookies et du localStorage dans un second contexte au même UA,
le refus du rejeu, la non-exportabilité de la clé, une XSS stockée filtrée et
le renouvellement automatique de la vraie application. Aucun e-mail ni service
client réel n’est utilisé. La CI lance ce test ainsi que la migration Redis réelle
et la sauvegarde/restauration réelle. Cela ne remplace pas un audit externe ou
un test d’intrusion du service déployé.
