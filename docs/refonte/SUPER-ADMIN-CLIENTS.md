# Gestion des entreprises clientes Radar

La liste `/admin/clients` remplace les anciens écrans `/workspaces`. Une fiche par entreprise regroupe les coordonnées, le responsable, les membres, les invitations, les commandes, les documents et les cent dernières opérations. `/admin/orders` centralise les commandes ; les anciennes URL redirigent. Les données métier des agences et leur facturation restent séparées des documents commerciaux de Radar.

## Droits et accès

Seul `is_superuser=true` donne accès aux nouvelles API de plateforme et aux écrans correspondants. Le rôle administrateur d’agence ne suffit pas. Une suspension bloque les routes de workspace, conserve les données et reste réversible. Elle ne désactive pas le compte global du responsable et ne suspend pas ses autres entreprises. Les pages `/account/workspaces` et `/account/security` restent accessibles indépendamment d’un workspace.

Les modifications de responsable conservent l’ancien responsable comme administrateur de l’espace et ne changent aucun rôle global. Les autorisations de places nécessitent une référence et ne peuvent pas réduire la limite sous l’occupation réelle.

## Invitation et première connexion

La création attribue Core par défaut, sans paiement fictif. L’invitation est confiée au worker Celery : seul son identifiant entre dans Redis. Pour un nouveau compte, le worker génère un mot de passe aléatoire valable 24 h, envoie les indications puis enregistre uniquement son empreinte. Une erreur fournisseur reste un échec visible, sans nouveau mot de passe utilisable enregistré. `sent` signifie accepté par le prestataire, pas livré dans la boîte de réception.

Un compte existant conserve son nom, ses identifiants et ses facteurs. Le renvoi est disponible sur la fiche, limité à un envoi par minute. Pour un compte encore en configuration, un renvoi réussi remplace le mot de passe temporaire et révoque les anciens accès. Pour un compte configuré, il renvoie les indications sans changer sa sécurité ; un lien de récupération séparé reste disponible.

Après connexion avec le mot de passe temporaire, le backend refuse l’accès métier tant que le mot de passe n’est pas remplacé. Le formulaire existant conserve sa politique de sécurité et demande un facteur déjà actif. La deuxième étape propose l’A2F ou une clé d’accès ; « Plus tard » permet de reporter cette étape uniquement. Les comptes existants ne sont pas forcés à recommencer ce parcours.

Les clés d’accès utilisent WebAuthn, avec vérification cryptographique, origine/RP dérivés de `FRONTEND_URL`, vérification utilisateur obligatoire, challenges liés au compte et à usage unique. Elles constituent un second facteur après la première étape de connexion. Leur ajout/retrait demande une vérification récente, met à jour la révision de sécurité et préserve la session courante. HTTPS est obligatoire en production. Les codes de secours sont présentés lors de leur génération. Aucun fournisseur SMS n’est simulé.

## Commandes, devis et contrats

Une commande démarre en attente et ne donne aucun droit. Un devis peut être créé depuis la fiche, avec plusieurs lignes, quantités, prix unitaires HT, TVA, validité et conditions saisis explicitement. Les calculs utilisent `Decimal` et un arrondi au centime par ligne. Le PDF est produit avec ReportLab à partir des données persistées : identité légale publiée de Radar, coordonnées client, référence unique, totaux et conditions. Il est téléchargeable en brouillon puis après émission. Un devis émis conserve ses instantanés ; pour corriger un document, créez un nouveau devis. Aucun tarif n’est inventé.

La publication préalable de l’identité légale de Radar est nécessaire ; avant émission, les coordonnées et conditions doivent être complètes. Le PDF n’est ni une facture ni une preuve de paiement. Le téléchargement exige les droits super-admin.

Un contrat signé à l’extérieur est déposé en PDF (8 Mo maximum, document lisible non chiffré), avec signataire, date, référence et commande. Ses octets originaux et leur empreinte sont conservés. Un contrôle manuel distinct avec référence est nécessaire. Ce contrôle **ne vérifie pas cryptographiquement une signature électronique** et ne remplace pas une acceptation réelle du client.

Pour valider un changement d’offre, l’administrateur choisit une acceptation Radar authentique compatible ou un contrat externe contrôlé, lié à la bonne entreprise, à la bonne commande et à la bonne offre. La référence de décision et la confirmation de contrôle sont obligatoires. Cette autorisation peut attribuer le plan ; elle n’invente jamais de paiement. Une extension personnalisée reçoit uniquement un accord commercial, sans activation générique de fonctionnalités. Le traitement technique des extensions demeure spécifique à chacune.

## Migrations et conservation

- `060_client_lifecycle` : suspension, première connexion, invitations. Valeurs par défaut compatibles pour les comptes existants.
- `061_passkeys` : identifiants WebAuthn et challenges temporaires.
- `062_platform_sales` : devis Radar, contrats externes et lien de preuve des commandes.

Les migrations n’effacent aucune donnée existante. Le downgrade refuse de supprimer les contrôles de première connexion/suspension en cours, l’historique d’invitations, des clés enregistrées ou des documents commerciaux. Un retour arrière après utilisation nécessite une procédure de conservation revue ; ne pas forcer la suppression de ces tables. Les archives de workspace continuent d’exclure les secrets et comptes globaux. Les documents commerciaux Radar nécessitent une restitution contrôlée par la plateforme, mentionnée dans la politique d’export, plutôt qu’une exposition à tous les administrateurs d’agence.

## Déploiement VPS

Dans le checkout existant `/opt/radar`, récupérer la branche puis lancer `bash scripts/deploy-client-admin.sh`. Le script sauvegarde PostgreSQL (sans stdin attaché), vérifie l’archive, conserve les images précédentes, compile les deux applications, applique les migrations et redémarre backend/worker/scheduler/frontend. Il conserve les volumes et le service MCP. Il ne restaure jamais une base automatiquement après une erreur. La sauvegarde contient des données personnelles : répertoire privé à conserver selon la politique opérateur.

Resend ou SMTP, le worker et le broker doivent être configurés. `FRONTEND_URL` doit correspondre exactement à l’origine HTTPS publique. Aucune nouvelle clé de paiement ou de SMS n’est requise. Après déploiement, vérifier `/admin/clients`, envoyer une invitation à un destinataire de test autorisé, terminer la première connexion, puis enregistrer et utiliser une clé sur un appareil compatible.

## Vérification

Tests backend : contrôles super-admin, séparation des entreprises, suspension/réactivation, invitations et refus fournisseur, mot de passe temporaire/expiration, remplacement obligatoire, WebAuthn ES256 réel, mauvaise origine, absence de vérification utilisateur, rejeu, expiration et compteur ; calculs décimaux, PDF lu avec pypdf, contrôles de contrats et commandes sans paiement fictif. Les tests navigateur utilisent exclusivement des réponses API explicitement simulées et un serveur local ; ils ne prouvent pas la livraison d’e-mails en production ni la compatibilité de chaque appareil WebAuthn.

La chaîne historique Alembic est vérifiée depuis six points de départ avec conservation de données, accord avec les modèles et refus des retours arrière destructifs. Les tests navigateur couvrent ordinateur, tablette et mobile, les devis téléchargeables, les erreurs visibles et l’ordre mot de passe obligatoire → facteur facultatif.

Validation locale du 19 novembre 2026 : **334 tests backend réussis**, build Next.js et typage réussis ; chaîne de migrations réussie depuis une base vide et cinq révisions historiques. Régressions navigateur réussies : nouvelle administration et première connexion à 1 440/768/390/320 px ; contrats/approbation, A2F, mots de passe, compte public et thèmes à 1 440/390 px. Les avertissements hérités de dépendances et de dates UTC naïves restent visibles dans la suite ; ils ne sont pas assimilés à des échecs fonctionnels. La livraison réelle d’une invitation et un authentificateur physique restent à vérifier sur le VPS après déploiement.

### Changement d’offre depuis la fiche

Un bloc « Changer l’offre » est visible directement sous le récapitulatif de chaque entreprise : choisir Core, Premium ou Business, puis « Appliquer la modification ». Une commande correspondante en attente est réutilisée ; sinon elle est préparée. La confirmation affiche l’ancienne et la nouvelle offre et exige la preuve contractuelle et la référence existantes. Annuler conserve la commande en attente et ne change aucun droit. Un refus backend reste visible dans la fenêtre, sans succès affiché. L’offre active se rafraîchit après validation ; si l’espace sélectionné est celui du compte courant, son cache d’abonnement est réinitialisé. Les contrôles super-admin et contractuels du backend restent ceux de la décision de commande.

### Arrivée après connexion et comptes collaborateurs

Dans Administration → Utilisateurs, le super-admin peut activer « Compte collaborateur » sur un compte. Ce réglage ne modifie aucun rôle ni membership. Un collaborateur arrive après connexion sur le choix de ses workspaces, même s’il n’en a qu’un. Un compte classique lié à un seul workspace actif est automatiquement dirigé vers celui-ci ; avec plusieurs workspaces, il choisit. Aucun espace et espace suspendu restent des états explicites, sans sélection automatique ni contournement. Les super-admins sans mode collaborateur conservent leur arrivée dans l’administration.

Les connexions par mot de passe, A2F, clé d’accès et SSO utilisent la même décision de destination. Le remplacement du mot de passe temporaire et les étapes de sécurité en cours gardent la priorité. Le choix manuel des espaces reste accessible depuis le compte. Un ancien workspace mémorisé ne remplace pas le choix demandé à un collaborateur. La requête des espaces utilise les appartenances effectives, sans `DISTINCT` sur les colonnes JSON PostgreSQL.

La migration `063_collaborator_entry` ajoute une préférence désactivée par défaut pour les comptes existants. Elle refuse un downgrade si des comptes utilisent ce réglage, pour éviter la perte silencieuse de leurs préférences. Le déploiement nécessite donc la reconstruction du backend et du frontend puis `alembic upgrade head`, déjà assurés par le script de déploiement.

Validation de ces ajouts : 336 tests backend réussis ; build frontend réussi ; scénarios navigateur réussis à 1 440/768/390/320 px pour changement d’offre, refus, annulation, réutilisation de commande, entrée automatique et sélection collaborateur, workspaces multiples et suspendus. Régressions A2F/SSO et contrats réussies à 1 440/390 px. Migration 063 vérifiée dans la chaîne historique, y compris le refus de perte d’une préférence utilisée. Les réponses des scénarios navigateur sont explicitement simulées ; aucune commande commerciale réelle ni e-mail réel n’a été envoyé par ces tests.

### Présentation de la gestion des utilisateurs

`/users` adopte le cadre des autres pages d’administration : marges et largeur cohérentes, recherche nom/e-mail, filtres mode/état, tableau sur grand écran et cartes sur mobile. Le rôle, le statut actif, le mode collaborateur et les fournisseurs réellement liés sont affichés séparément. Les états de chargement, de liste vide et d’échec sont explicites.

La fenêtre « Modifier l’utilisateur » regroupe identité, accès et arrivée, puis sécurité. Le réglage « Compte collaborateur » est ici. « Appliquer les modifications » enregistre réellement le choix et conserve la fenêtre et son erreur en cas de refus. Aucun mot de passe n’est envoyé lors d’une modification ordinaire. Sa réinitialisation doit être activée explicitement, avec critères et confirmation ; son propre mot de passe passe par la page de sécurité et ses contrôles A2F.

La désactivation/réactivation demande une confirmation et conserve les données. La désactivation révoque les sessions : elles ne redeviennent pas valides après réactivation. La désactivation de son propre compte est refusée côté backend. La gestion globale des comptes et des réglages administratifs exige désormais `is_superuser=true` sur toutes les routes `/users`, plutôt que le seul rôle administrateur d’agence. Les doublons d’e-mail sont refusés sans écraser un compte existant. L’ancien endpoint de suppression est conservé et restreint au super-admin ; la page privilégie la désactivation réversible.

La nouvelle page Utilisateurs est vérifiée en navigateur local à 1 440/768/390/320 px : erreur de chargement et reprise, recherche/filtres, enregistrement explicite du mode collaborateur, refus serveur sans fermeture du formulaire, absence de mot de passe dans une modification ordinaire, création avec critères et confirmation, désactivation/réactivation et protection de son propre compte. Le thème sombre du formulaire est aussi vérifié. Les fixtures sont signalées TEST et ne modifient aucun compte réel. Les nouveaux contrôles backend incluent un refus de gestion globale par un administrateur d’agence et une véritable reconnexion après réactivation, avec maintien du refus des anciens jetons.

Validation finale : **337 tests backend réussis**, build Next.js et typage réussis, régressions navigateur de la page Utilisateurs réussies aux quatre formats. Aucun changement de données ni déploiement n’a été exécuté sur le VPS pendant ces vérifications.

### Suppression d’un espace suspendu

Une fiche suspendue affiche « Supprimer l’espace ». L’action est réservée au super-admin et demande de retaper exactement le nom, de saisir un motif et de confirmer le retrait. Le backend verrouille et relit l’espace : actif, il refuse la suppression, y compris si l’interface avait conservé un ancien état suspendu.

Il s’agit d’une **suppression logique**, conforme à la conservation des données : `deleted_at` et `deleted_by` retirent l’espace des listes, du sélecteur et des accès ordinaires. Les comptes, memberships, projets, historiques, documents financiers et contractuels sont conservés ; aucun fichier externe ni intégration n’est effacé. L’ancienne URL DELETE applique exactement cette même règle. Elle ne permet plus une suppression physique par un propriétaire d’agence.

Les lectures ORM de Workspace excluent les espaces supprimés dans le backend et les workers. Les API historiques des espaces vérifient l’existence de l’espace avant d’accéder à ses enfants. Une décision commerciale sur un espace supprimé est refusée ; sa fiche ne permet plus de le réactiver. Le journal conserve l’auteur et le motif du retrait. Les opérations externes déjà engagées ne sont pas annulées automatiquement et aucun effacement de données externes n’est demandé.

La restitution et la conservation restent des opérations contrôlées de plateforme. L’outil CLI `tools/maintenance/list_clients.py` conserve son inventaire explicitement ciblé et sa protection PostgreSQL en lecture seule, y compris pour un espace retiré ou un ancien schéma. Ce comportement opérateur n’est pas une route d’accès utilisateur. Une restauration éventuelle nécessite une procédure opérateur explicite ; aucun bouton de restauration automatique n’est ajouté.

Appliquer la migration `065_workspace_deletion`. Son downgrade refuse de retirer les marqueurs si des espaces sont supprimés, pour éviter leur réapparition automatique. Les exports de workspace gardent leur liste explicite de champs et excluent les marqueurs opérateur. Aucune suppression de données de production n’a été exécutée pendant l’implémentation.

Après utilisation de cette suppression logique, ne pas redéployer une image d’application antérieure à la migration 065 : elle ne connaît pas les marqueurs de retrait et pourrait réafficher un espace ou permettre sa réactivation. Le retour arrière doit conserver le contrôle de retrait ou passer par une procédure opérateur explicite. Le script de déploiement ne restaure jamais automatiquement une ancienne image ou la base.

Validation du retrait des espaces : **344 tests backend réussis**, build Next.js et typage réussis ; chaîne historique Alembic validée avec refus du rollback qui réactiverait un espace retiré. Scénarios navigateur à 1 440/768/390/320 px réussis : absence du bouton sur espace actif, saisie du nom, confirmation, refus serveur conservant la fenêtre et redirection après retrait. Les tests de conservation couvrent comptes, memberships, compteur de factures et demandes commerciales ; les autres entreprises restent accessibles. Les scénarios utilisent exclusivement des bases de test et des API navigateur simulées.

### Correctif du contexte sélectionné pour un collaborateur multi-workspace

Un même compte autorisé dans A et B pouvait demander B puis recevoir des projets de A : une dépendance validait B, mais un helper appelait ensuite `resolve_workspace_id` sans argument et sélectionnait le premier workspace du compte. Cette deuxième résolution écrasait le contexte de la session de requête.

Le résolveur conserve désormais le workspace déjà validé dans `Session.info` pour tous les appels imbriqués. Une tentative de changer explicitement de workspace pendant cette même requête est refusée, sans altérer le contexte établi. Une autre requête peut naturellement sélectionner un autre workspace après validation de son appartenance. Les contrôles de permissions, suspension et suppression restent appliqués.

La carte du workspace dans la barre latérale ouvre maintenant le sélecteur existant. Les tests backend reproduisent l’erreur avant correctif, puis vérifient B → A → B, le détail et la modification d’un projet A refusés dans B, la création persistée dans B et le refus d’un client A pour une création B. Aucun projet de production n’est déplacé par le correctif et aucune migration n’est nécessaire.

Validation du contexte sélectionné : **348 tests backend réussis**, build Next.js et typage réussis ; tests navigateur à 1 440/390 px avec sélection initiale de B, navigation côté client B → A → B et réponse A retardée qui ne remplace jamais la vue B. Les réponses navigateur sont des fixtures explicites ; les régressions de résolution et d’écriture sont testées sur PostgreSQL réel de test. Après déploiement, recharger la page puis sélectionner de nouveau le workspace pour renouveler la vue éventuellement conservée dans l’onglet.
