# Demandes de contact dans Radar

Le formulaire `/contact` enregistre les demandes dans PostgreSQL et ne dépend plus de `CONTACT_RECEIVER_EMAIL`, de Resend ni de SMTP pour accepter une demande. Son succès n’est affiché qu’après validation de la transaction. En cas de panne, les champs restent dans la page et une référence technique peut être communiquée à l’opérateur. Aucune adresse de réception n’est choisie automatiquement.

Le super-admin dispose de `/admin/contact-requests`, avec recherche, filtres et compteur des dossiers à ouvrir. Le dossier contient les informations réellement saisies et la version de notice présentée. Seul `is_superuser=true` donne accès à la liste, au compteur, au détail, à l’ouverture et aux changements d’état. L’administrateur d’une agence n’y a pas accès.

## Première ouverture et accusé par e-mail

La navigation dans le dossier déclenche une commande POST d’ouverture, distincte d’une simple lecture GET ou du préchargement du lien. Une transaction verrouille la demande et enregistre la première date et l’administrateur. Cette première ouverture seulement programme un job Celery contenant l’identifiant du dossier, sans message ni adresse dans le broker.

Le visiteur reçoit : « Votre demande a bien été ouverte par notre équipe. Nous vous contacterons prochainement pour la traiter. » Cela ne confirme ni commande commerciale, ni devis, ni paiement. Le message ne recopie pas le contenu de sa demande. Les ouvertures suivantes, la clôture et la réouverture ne déclenchent pas de nouvel accusé.

Le worker utilise Resend configuré, sinon le SMTP configuré. Resend reçoit une clé d’idempotence liée au dossier ; le job réclame son traitement avant l’envoi pour éviter les doublons dus à une redélivrance du job. Aucun transport alternatif n’est essayé après une tentative au résultat incertain. Il n’y a pas d’envoi réel dans les tests.

Les états restent explicites : non demandé, en attente, en cours, transmis au service d’envoi, échec. Un refus fournisseur ou une erreur de queue conserve le dossier. Le super-admin peut relancer un accusé en échec, avec une minute entre deux demandes de relance. « Transmis » signifie accepté par le fournisseur, pas livré dans la boîte de réception. Un worker interrompu après sa prise en charge peut laisser un état « en cours » à examiner par l’opérateur ; les consultations suivantes ne renvoient pas aveuglément le message.

## Exploitation et conservation

Appliquer `064_contact_inquiries` avant de lancer le nouveau backend, puis reconstruire/redémarrer backend, worker, scheduler et frontend avec le script de déploiement existant. La variable `CONTACT_RECEIVER_EMAIL` peut rester pour compatibilité mais n’est plus utilisée par ce formulaire. Les e-mails d’ouverture nécessitent uniquement le transport d’e-mails déjà configuré dans Radar et un worker qui traite la queue `celery`.

Les demandes contiennent des données personnelles : elles sont exclues des exports de workspace car elles appartiennent au suivi global de la plateforme. Les demandes d’accès aux données et les durées de conservation doivent être traitées par la plateforme selon sa politique publiée. Aucun effacement automatique ni délai de conservation arbitraire n’est introduit. La migration refuse de supprimer une table contenant des demandes lors d’un downgrade ; leur conservation doit être organisée explicitement.

Les anciennes tentatives refusées pour absence de destinataire n’ont pas été enregistrées par l’ancien parcours : le visiteur doit renvoyer sa demande depuis les champs conservés sur sa page après déploiement. Aucun ancien dossier n’est inventé à partir d’un échec d’envoi.

Validation locale : **343 tests backend réussis**, chaîne historique Alembic depuis six états réussie, y compris refus du downgrade d’une boîte utilisée ; build Next.js et typage réussis. Tests navigateur du formulaire à 1 440/390 px et de la boîte/dossier à 1 440/390/320 px réussis. Huit tests du client HTTP couvrent l’accusé de réception applicatif, les erreurs serveur/proxy/réseau, les refus de validation et les références techniques masquées. Les transports e-mail et le broker sont simulés dans les tests métier ; la livraison réelle est à vérifier après déploiement avec une demande de test autorisée.
