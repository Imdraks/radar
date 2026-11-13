# Procédure préalable à l’ouverture commerciale B2B

Version du 13 novembre 2026. Responsable à désigner par l’éditeur ; aucune opération de production exécutée par cette documentation.

## Identité, contrats et infrastructure

1. Renseigner les informations publiques vérifiées dans `frontend/src/config/legal.json`. Ne pas copier une identité d’exemple, un RCS déduit de l’adresse ou un numéro de TVA calculé. Déclarer `publisherType` selon l’entreprise réelle ; capital applicable aux sociétés.
2. Faire valider CGV B2B, contrat/DPA article 28, annexes sécurité, sous-traitants ultérieurs, transferts, rétention et réversibilité. Les pages de validation du dépôt ne sont pas ces contrats signés. Conserver version et preuve d’accord avant activation ; une visite ou un dépôt de demande ne vaut pas achat.
3. Identifier hébergeur, email, analytics, IA, Google, stockage, collecteurs et sauvegardes réellement utilisés, leurs pays et garanties. Documenter qui est responsable ou sous-traitant pour chaque finalité, le registre, les bases légales et analyses nécessaires.
4. Définir les durées pour prospects/contact, comptes, contenus de workspace, logs, demandes de droits, preuves contractuelles, documents financiers et sauvegardes. Ne pas appliquer une durée comptable à toutes les données personnelles.
5. Configurer `CONTACT_RECEIVER_EMAIL` avec un véritable destinataire et le service email correspondant. Sans configuration, le formulaire répond par une indisponibilité explicite. Recetter l’envoi et les erreurs avec des comptes de test autorisés.
6. Vérifier TLS, secrets, habilitations, supervision, sauvegardes et restauration sur l’infrastructure retenue. Contrôler les traceurs réseau avant choix, après refus, après accord et après retrait.
7. Choisir la plateforme agréée et qualifier les besoins de facturation électronique des clients. Valider mentions, taxes, numérotation, archivage et rectifications avec le conseil comptable. Le PDF et un paiement manuel ne sont pas un reçu bancaire ou réglementaire.
8. Revoir le périmètre IA, accessibilité, Data Act et autres textes selon l’entreprise et les usages réels. Un nouveau public B2C exige une revue distincte.

## Demandes de droits et fin de service

- Désigner un opérateur et un suppléant ; surveiller quotidiennement `/admin/privacy-requests` et la boîte de contact publiée. Une personne extérieure/non connectée doit pouvoir utiliser ce contact ; ne pas exiger la création d’un compte pour exercer un droit.
- Les demandes `received` / `in_progress` sont prioritaires. Vérifier l’identité de façon proportionnée si nécessaire, distinguer demande personnelle et mandat d’un client responsable de traitement, et préserver les données d’autres personnes.
- L’échéance du portail est un repère d’un mois calendaire ; informer la personne des suites et, lorsque légalement justifiée, d’une extension dans les délais. Résiliation et changement de prestataire ont des règles et engagements distincts.
- Rechercher les données pertinentes, y compris systèmes externes, et expliquer les exceptions ou limites. Le téléchargement JSON du compte est partiel : ne jamais le présenter comme une réponse complète sans examen.
- Pour rectification/effacement/opposition, documenter les systèmes concernés et les obligations de conservation. Restreindre ou archiver si approprié ; ne pas supprimer des factures, des comptes tiers ou des sauvegardes sans procédure validée.
- Pour réversibilité, établir données et actifs exportables, formats, fichiers Drive et autres tiers, destination, vérification de restitution et fin de conservation ; appliquer les délais Data Act si le service y est soumis. Tester un export complet sur un workspace de recette avant tout engagement.
- Répondre via l’écran opérateur avec une référence de dossier et les actions réellement réalisées. `answered` est un état saisi, pas la preuve d’un effacement ou d’une livraison d’email. Conserver la preuve du canal de notification effectivement utilisé et limiter les informations sensibles dans le portail.
- Appliquer la durée de conservation des dossiers définie par l’éditeur ; auditer l’accès opérateur. Aucune purge automatique nouvelle n’est activée par cette livraison.

## Incident de données personnelles

Contenir, préserver les preuves sans divulguer de secrets, établir périmètre/personnes/conséquences et mesures, informer le responsable désigné. En qualité de sous-traitant, notifier le responsable de traitement sans retard indu ; en qualité de responsable, évaluer la notification à l’autorité sous 72 heures après connaissance lorsque requise, et l’information des personnes en cas de risque élevé. Documenter aussi les incidents non notifiés et la justification. Vérifier les engagements contractuels, canaux, sauvegardes et procédures avant ouverture ; ne pas promettre que le logiciel réalise automatiquement ces notifications.

## Contrôle final

Exécuter `python scripts/check_release.py` après validation réelle de tous les éléments. Faire une recette sur l’instance de production préparée avec comptes autorisés, contrôler les documents publics et la preuve d’acceptation des contrats. La réussite du script ou de la CI ne donne pas, à elle seule, une autorisation juridique de vente. Maintenir une revue lors d’un changement de prestataire, finalité ou réglementation.
