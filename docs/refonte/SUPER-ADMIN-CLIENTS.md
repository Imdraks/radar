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
