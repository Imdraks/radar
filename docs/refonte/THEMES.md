# Thèmes clair et sombre

`next-themes`, au niveau des Providers, est l’unique propriétaire du thème HTML.
Le menu commun affiche le choix courant : Clair, Sombre ou Système. Système
suit effectivement `prefers-color-scheme`, y compris ses changements en direct.
L’administration utilise le même menu et ne modifie plus les classes HTML ni
le stockage elle-même.

Les pages publiques et la documentation conservent la DA claire via
`forcedTheme="light"`. Cette présentation ne change pas le choix mémorisé :
le retour à l’application restaure automatiquement le thème de l’utilisateur.
Les wrappers publics ne sauvegardent/restaurent plus une ancienne liste de
classes HTML, qui pouvait entrer en conflit avec le provider.

La palette complète est définie dans `radar-brand.css` : fonds, cartes,
popovers, textes, champs, bordures et états sémantiques. Le bouton primaire
en thème sombre utilise un texte foncé sur violet clair. Les règles globales
imposant une couleur à tous les paragraphes/liens sombres ont été retirées,
pour préserver les couleurs explicites des boutons et notifications.

`radar-theme-legacy.css` adapte les anciennes classes de surfaces et de texte
dans les seuls espaces privés. Cette compatibilité ne filtre ni n’inverse
les images, QR codes, SVG ou canvas. Les styles des composants modernes
continuent d’utiliser les tokens sémantiques ; les anciennes classes pourront
être remplacées progressivement lors des modifications des écrans concernés.
Les champs noirs des événements/dépenses et des décisions d’abonnement ont
été remplacés directement par des couleurs sémantiques. Les notifications
partagées utilisent une surface de thème et une bordure de statut.

Recette locale : `scripts/theme_ui_smoke.py`, inclus dans la CI, contrôle
ordinateur et mobile : persistance après rechargement, suivi système en direct,
aller-retour vers la documentation, menu porté, anciennes cartes de projets,
formulaire et administration. Des contrastes texte/fond représentatifs sont
mesurés (minimum 4,5:1). Ces contrôles ne constituent pas un audit d’accessibilité
exhaustif. Les API sont des fixtures et aucun compte de production n’est utilisé.

Aucune migration ou clé supplémentaire. Reconstruire l’image frontend pour
déployer les animations et les corrections de thème ensemble.
