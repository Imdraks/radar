# Double authentification : application, e-mail et SMS

## Périmètre livré

Le réglage reste attaché au compte, indépendant de l'abonnement et du workspace.
L'utilisateur peut activer plusieurs méthodes : application TOTP, e-mail vérifié
et numéro SMS vérifié. Les codes de secours servent de recours à usage unique.
La page Paramètres > Sécurité et le formulaire de connexion utilisent le nouveau
parcours. Le guide public est `/doc/double-authentification`.

Les e-mails réutilisent Resend si configuré, sinon le SMTP existant avec TLS ou
SSL. L'adaptateur SMS fourni est Twilio, désactivé par défaut. Aucun compte SMS,
achat, prix ni fournisseur actif n'a été créé. Le propriétaire n'a pas encore de
fournisseur SMS. Sans configuration, la méthode est indisponible dans l'interface
et l'API refuse son activation ; elle ne prétend jamais avoir envoyé un code.

## Protections

- Mot de passe vérifié avant émission d'un défi de connexion. Avec Google/Apple,
  aucun jeton de session n'est émis avant le second facteur requis.
- Défis opaques aléatoires de cinq minutes, hachés en base, liés au compte, à un
  usage et à sa version de sécurité. Ils ne sont jamais des jetons d'API.
- Mot de passe absent du stockage de l'étape MFA ; le formulaire le vide après
  validation du premier facteur. Les preuves et codes de secours ne sont pas
  persistés dans localStorage/sessionStorage.
- OTP de livraison hachés avec HMAC et secret serveur, jamais stockés en clair,
  jamais retournés dans une réponse ou un log. Le code renvoyé remplace l'ancien
  sans prolonger la durée du défi.
- Limites en base partagées entre processus : cinq mauvaises vérifications sur
  une fenêtre de dix minutes, soixante secondes entre envois, trois envois par
  défi, cinq envois par heure et compte. Un échec fournisseur consomme aussi son
  budget. Les limites par IP existantes restent en complément.
- Verrou de ligne du compte pour les preuves, les budgets et les codes à usage
  unique. Un test PostgreSQL concurrent vérifie qu'un même code de secours ne
  peut aboutir deux fois.
- Réauthentification avant ajout/retrait d'une méthode ou régénération des codes.
  Mot de passe si présent, puis facteur déjà actif. Un compte uniquement SSO doit
  avoir une authentification récente ; un refresh n'en rafraîchit pas la date.
- Secret TOTP neuf préparé séparément, sans remplacer une méthode active. E-mail
  et téléphone attachés à leur destination confirmée, pas à un champ arbitraire.
- Secrets TOTP neufs et coordonnées de facteurs chiffrés avec le mécanisme Fernet
  existant et `SECRET_KEY`. Les anciens secrets TOTP restent compatibles et sont
  chiffrés lors de leur utilisation valide.
- Nouveaux codes de secours à 64 bits d'entropie, hachés avec HMAC, affichés une
  seule fois. Les anciens codes restent valables puis sont hachés après une
  vérification MFA réussie ; un code utilisé est supprimé sous verrou.
- `mfa_version` invalide accès, refresh et défis antérieurs après modification de
  sécurité. La session courante reçoit de nouveaux jetons. Les connexions WebSocket
  utilisent le même contrôle et le revérifient lors des battements existants.
- Réponses d'authentification non stockables, redirections SSO par fragment plutôt
  que jetons en query string, suppression du fragment par le navigateur. Erreurs
  fournisseurs et erreurs SSO génériques, sans corps, secret ou stack relayé.
- Journal des activations, retraits et régénérations sans coordonnées ni codes.
  Défis expirés depuis plus de 24 heures purgés quotidiennement à 04:15 par Beat.
  Le respect de cette rétention exige Beat et un worker opérationnels.
- Défis et matériel d'authentification exclus des archives workspace et des
  exports de profil. Les vues de statut ne montrent que des destinations masquées.

## API

Toutes les routes sont sous `/api/v1/auth/mfa`.

| Route POST | Contexte / rôle |
| --- | --- |
| `/options` | Défi de connexion : méthodes et destinations masquées |
| `/send` | Défi de connexion, gestion ou enrôlement ; envoi borné |
| `/complete` | Termine un défi de connexion et émet les jetons |
| `/reauth/start` | Session authentifiée ; vérifie mot de passe ou récence SSO |
| `/reauth/complete` | Session + défi de gestion ; vérifie le facteur actif |
| `/enroll/start` | Session + preuve de gestion unique ; prépare une méthode |
| `/enroll/complete` | Session + défi d'enrôlement ; confirme puis active |
| `/disable` | Session + preuve de gestion unique ; retire une méthode |
| `/recovery/regenerate` | Session + preuve de gestion unique ; remplace les secours |

`GET /status` exige une session et retourne méthodes, disponibilités de livraison
et destinations masquées. Les API de gestion n'acceptent pas d'identifiant de
compte ou de workspace pour agir sur un tiers.

`POST /auth/login` reste compatible avec `totp_code` pour les clients TOTP/secours
existants. Sinon, il retourne `requires_2fa`, `temp_token`, `methods` et
`destinations`. Un client e-mail/SMS doit suivre le défi explicite. Le refresh
utilise désormais le corps JSON `{"refresh_token":"…"}`, comme le frontend et
le bridge MCP existants, et ne renouvelle pas la preuve de récence SSO.

Les anciennes mutations `/auth/2fa/setup`, `/enable`, `/disable`, `/verify` et
`/regenerate-backup-codes` restent authentifiées mais retournent 410. Leur ancien
flux pouvait écraser un secret actif sans réauthentification. `/auth/2fa/status`
reste une lecture compatible. Déployer le frontend et le backend ensemble.

## Configuration d'envoi

Ne pas committer les valeurs réelles ni les transmettre dans une conversation.
Pour l'e-mail, conserver la configuration Resend existante (`RESEND_API_KEY`,
`RESEND_FROM_EMAIL`) ou configurer `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM_EMAIL` et `SMTP_USE_TLS`. Le SMTP sur port 587 exige
STARTTLS ; le port 465 utilise SSL avec validation de certificat. Un SMTP sans
transport chiffré n'est pas proposé pour les codes.

Le SMS reste inactif avec les valeurs vides suivantes :

```dotenv
MFA_SMS_PROVIDER=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

Après choix et configuration d'un compte fournisseur par l'opérateur, renseigner
`MFA_SMS_PROVIDER=twilio` et les trois valeurs de ce compte. Configurer les pays
autorisés et les plafonds de dépense du fournisseur. Valider ses conditions et
mettre à jour l'information sur les sous-traitants réellement utilisés avant
d'activer le canal pour les clients. Aucun coût SMS n'est inclus ou simulé par
ce code. Tester un envoi réel autorisé avant d'annoncer le service opérationnel.

Les Codespaces ne réutilisent pas les identifiants de production. Les nouvelles
variables sont filtrées ; seules les variantes `RADAR_TEST_*` explicitement
définies sont transmises au backend, jamais au frontend.

## Migration 057 et mise en production

1. Sauvegarder PostgreSQL, les fichiers de déploiement et les clés de chiffrement.
   Garder `SECRET_KEY` et `JWT_SECRET_KEY` cohérents entre les instances. Une perte
   de la clé de chiffrement rend les facteurs chiffrés inutilisables.
2. Identifier la révision Alembic et le schéma réels du VPS. Il a reçu des patches
   hors Git : ne pas appliquer un faux stamp ni remplacer ses configurations.
3. Construire une image backend contenant la migration 057 et la tester sur une
   restauration de la sauvegarde. La migration est additive : six colonnes de
   compte et une table de défis, sans suppression des comptes/workspaces.
4. Passer la migration avec cette nouvelle image, puis déployer le backend, les
   workers/Beat et le frontend correspondant. Les comptes TOTP historiques voient
   leur version de sécurité passer à 1, ce qui force la reconnexion de sessions
   émises avant la correction de l'ancien contournement SSO.
5. Mettre à jour le MCP avec le correctif ci-dessous avant d'utiliser des comptes
   protégés uniquement par e-mail ou SMS dans son formulaire OAuth.
6. Vérifier une vraie connexion, une activation et une récupération sur un compte
   de contrôle. Vérifier SSO si configuré et un envoi réel pour chaque fournisseur
   activé. Conserver une méthode accessible et les codes de secours.

Le downgrade automatique est possible uniquement avant utilisation des nouveaux
états. Il refuse les facteurs de livraison actifs, les formats chiffrés/hachés ou
une version de révocation non nulle. Revenir aveuglément à l'ancien backend peut
ignorer les facteurs e-mail/SMS ou rendre les secrets illisibles : garder une
version compatible en cas de correctif, ou organiser une restauration coordonnée
après examen opérateur. Une simple ancienne image n'est pas un rollback sûr.

La purge ne réinitialise jamais un facteur et n'est pas une récupération de compte.
En cas de perte de toutes les méthodes et des secours, une intervention avec
vérification d'identité doit suivre la procédure opérateur ; aucun contournement
public par e-mail ou identifiant n'est ajouté.

## Compatibilité du MCP installé séparément

`integrations/chatgpt-mfa-patch/` adapte uniquement `RadarAPI.login` du fichier
`radar.mjs` fourni par le propriétaire et ajoute `mfa-login.mjs`. OAuth, le store
et les scopes de lecture/écriture restent inchangés. Par défaut il utilise TOTP
si actif, sinon e-mail puis SMS. Un code de secours est accepté sans envoi.
Le formulaire existant reçoit le code dans son champ de double authentification.

Les preuves sont conservées moins de cinq minutes en mémoire du processus, avec
une clé de correspondance HMAC éphémère, sans mot de passe stocké en clair. Les
envois ne sont pas répétés à chaque soumission du formulaire. Un redémarrage du
connecteur peut nécessiter de recommencer la vérification.

Sur une copie du connecteur, fournir les deux fichiers du correctif puis lancer :

```bash
sudo python3 install.py /opt/radar/chatgpt-connector
```

Après validation, arrêter seulement le MCP, relancer avec `--apply`, puis
reconstruire et redémarrer `mcp` avec les deux fichiers Compose déjà utilisés.
Une sauvegarde de `radar.mjs` est créée dans `.mfa-patch-backups/<date>/`. Un
fichier non reconnu est refusé. Ce correctif exige le nouveau backend MFA.

## Validation et limites

Suite backend complète sur PostgreSQL jetable, tests de migration historiques,
test de consommation concurrente, tests HTTP fournisseurs avec transports simulés,
tests navigateur de connexion/secours/réauthentification/activation à 1440 et
390 pixels, typage et build frontend. Les scripts et la CI incluent ces contrôles.
Sept tests Node vérifient l'adaptation du login MCP ; sa transformation a été
contrôlée sur le fichier complet transmis par le propriétaire.

Les fournisseurs réels, l'application mobile de l'utilisateur, les callbacks
Google/Apple réels et le formulaire OAuth distant du VPS ne sont pas disponibles
dans ce banc de test. Aucun courriel ou SMS réel n'a été envoyé. Aucun nouveau
code, schéma, fournisseur ou patch MCP n'a été installé sur le VPS pendant ce
travail. Les tests ne constituent pas une certification d'authentification ni une
attestation de conformité juridique.
