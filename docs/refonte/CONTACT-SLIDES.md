# Contact en plusieurs étapes

La page `/contact` devient une conversation en six étapes : nom, e-mail,
agence/téléphone, offre, message et récapitulatif. L’esthétique reprend une
surface blanche, de grands espaces, des champs arrondis et le violet Radar.
Les transitions sont courtes et désactivées en mouvement réduit. Aucun
défilement ou raccourci global n’est intercepté.

Le nom, l’e-mail et le message restent obligatoires ; les autres informations
restent facultatives. Les limites correspondent au contrat de l’API existante.
Les réponses restent uniquement dans l’état de la page, sans stockage des
coordonnées dans localStorage. Retour arrière et édition depuis le récapitulatif
conservent les données. L’envoi exige une confirmation finale explicite.

Les URLs `?plan=core|premium|business|custom` préremplissent l’offre ; une valeur
inconnue est ignorée. `?offer=mcp` conserve le contexte commercial du connecteur.
Sans JavaScript, les actions restent désactivées et un lien vers le contact
publié est proposé ; les coordonnées ne partent pas dans une query string.

Le POST JSON `/api/v1/contact` et la version de notice `2026-11-13` sont conservés.
Une réponse HTTP réussie doit également contenir `status: "ok"` avant la
confirmation. Les erreurs gardent le récapitulatif et permettent de réessayer ;
les doubles soumissions pendant un envoi sont bloquées. La confirmation signifie
que le backend a accepté la remise au fournisseur, pas que le destinataire a
effectivement lu le message. Aucun délai de réponse commercial n’est inventé.

Pour l’envoi réel, le backend existant nécessite `RESEND_API_KEY`,
`RESEND_FROM_EMAIL` sur un domaine vérifié et `CONTACT_RECEIVER_EMAIL`.
Ce changement ne configure pas ces secrets et ne modifie pas l’API.

Recette : `scripts/contact_ui_smoke.py` avec un frontend local et des réponses
API explicitement simulées. Elle couvre ordinateur/mobile, clavier, validation,
retour/édition, préremplissage, champs facultatifs, erreurs et réponse ambiguë,
absence de double envoi et payload complet. Le test est intégré à la CI.
Le contrôle des pages publiques est adapté à la première étape réellement visible.

Déploiement : aucune migration ni dépendance supplémentaire ; reconstruire
uniquement l’image frontend après intégration.
