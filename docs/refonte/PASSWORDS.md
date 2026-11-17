# Mot de passe : récupération et changement depuis le compte

Le lien « Mot de passe oublié ? » est disponible sur `/login`. Le formulaire
`/forgot-password` fait une demande à l’adresse saisie. Le worker crée le jeton
uniquement pour un compte actif et autorisé, puis remet le message au prestataire.
Le lien expire **15 minutes après sa création**, même si le message tarde à arriver.
Il ne sert qu’une fois. Après émission réussie d’un nouveau lien, les anciens liens
sont invalidés. Un échec d’envoi ne désactive pas un ancien lien encore valide.

Les demandes publiques suivent le même chemin de mise en file pour toutes les
adresses, sans consultation préalable des comptes. La réponse HTTP ne confirme ni
l’existence d’un compte ni la réception d’un message. Une configuration d’envoi
absente ou un broker indisponible produit une erreur 503 générale, identique pour
toutes les adresses. Les erreurs fournisseurs sont journalisées sans destinataire,
corps de réponse, mot de passe ou jeton. Les demandes connues sont limitées à une
par minute et cinq par heure ; les échecs d’envoi consomment ce budget. La limite IP
existante est conservée en complément.

## Politique unique

`app/core/passwords.py` est la source des critères : 12 caractères minimum,
majuscule ASCII, minuscule ASCII, chiffre ASCII, caractère spécial et au maximum
72 octets UTF-8 (limite bcrypt). Une petite liste de mots de passe courants est
refusée ; elle ne constitue pas une recherche exhaustive de mots de passe compromis.
Les deux saisies doivent être identiques et le nouveau mot de passe différent du
précédent. Les critères sont renvoyés au frontend par `GET /auth/password-policy`.
Les schémas de création/modification des utilisateurs et la création/réinitialisation
de mots de passe par l’administration réutilisent cette validation. Les anciens mots
de passe ne sont pas invalidés uniquement pour leur ancien format.

## Depuis les paramètres

Dans Paramètres → Compte, le formulaire exige l’ancien mot de passe et deux saisies
du nouveau. La vérification est attachée au compte connecté, indépendamment du
workspace sélectionné. Si une A2F est active, la preuve de gestion à usage unique
n’est émise qu’après vérification d’un facteur actif ou d’un code de secours. Le
backend exige cette preuve et revérifie l’ancien mot de passe : un appel direct à
l’API ne contourne pas l’A2F. Le bouton de validation n’enregistre rien avant la fin
de ces vérifications. Les mauvaises preuves ne sont pas rejouées automatiquement
par l’intercepteur HTTP frontend.

Le changement préserve uniquement la session courante avec de nouveaux jetons.
Toutes les autres sessions et toutes les autorisations de navigateur de trente
jours sont révoquées. Les preuves de sécurité en attente sont invalidées. Une
réinitialisation par e-mail révoque toutes les sessions et ne connecte pas
automatiquement le compte. Dans les deux cas, les facteurs A2F et les codes de
secours non utilisés restent configurés. Un compte SSO sans mot de passe peut en
définir un par le lien e-mail, sans supprimer sa connexion Google ou Apple.

## Jetons et confidentialité

Le jeton aléatoire est généré dans le worker, puis seule son empreinte SHA-256 est
stockée dans `mfa_challenges` avec le type `password_reset`, l’utilisateur, la version
de sécurité et l’expiration. Aucun jeton de récupération n’est placé dans les
arguments ou résultats du broker. La table existante est déjà exclue des exports
workspace et purgée après expiration plus la rétention prévue de 24 heures.

Le lien utilise l’origine `FRONTEND_URL` configurée, jamais l’en-tête Host fourni
par l’appelant. Le jeton est dans le fragment du lien (`#token=…`), retiré de la
barre d’adresse dès lecture, conservé uniquement en mémoire et envoyé en corps POST.
La page de réinitialisation n’est pas indexable ni mise en cache ; elle définit
`Referrer-Policy: no-referrer`. Les pages de récupération n’activent pas les scripts
Analytics. Aucun mot de passe ou lien brut n’est ajouté au journal d’activité.

## API sous `/api/v1`

- `GET /auth/password-policy` : critères publics.
- `GET /auth/password/status` : indique au compte connecté s’il a un mot de passe.
- `POST /auth/forgot-password` : `{email}` ; 202 neutre si la demande est mise en file.
- `POST /auth/reset-password` : `{token,new_password,confirm_password}` ; aucun jeton de connexion en réponse.
- `POST /auth/password/change` : `{current_password,new_password,confirm_password,management_token?}` ; session courante renouvelée. La preuve de gestion est obligatoire avec A2F.

## Déploiement

Aucune nouvelle table ni migration : l’instance doit déjà être en révision 058
(A2F et sessions révocables). Déployer ensemble le backend, le frontend et les
workers. Le worker doit importer `app.workers.password_tasks` et consommer la file
par défaut `celery`, comme les autres tâches non spécialisées. Le scheduler déjà
configuré conserve la purge des preuves expirées. Réutiliser les secrets existants.

Configurer Resend (`RESEND_API_KEY`, expéditeur validé), ou le SMTP existant avec
TLS/SSL, ainsi qu’une `FRONTEND_URL` HTTPS correcte. Ne jamais publier les valeurs
secrètes dans le dépôt. Un broker et un worker actifs sont requis. Sans fournisseur
réel, aucun envoi n’est simulé en production. Les tests emploient explicitement des
prestataires et des réponses navigateur simulés ; aucun e-mail réel n’est envoyé.

Le correctif du message A2F publié précédemment ne déploie pas ces nouveaux parcours.
Ne pas utiliser un ancien script ciblé pour annoncer leur mise en production.
