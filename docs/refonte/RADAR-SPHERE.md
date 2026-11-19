# Mascotte Radar — sphère vivante

La mascotte est un composant SVG/CSS réutilisable :
`frontend/src/components/mascot/RadarSphere.tsx`. Aucun média externe, SDK,
service IA, microphone ou nouvelle clé API n’est nécessaire.

## Intégration

- Le bouton d’aide de la barre de l’application affiche une sphère de 30 px.
- Son activation ouvre le guide de bienvenue, où elle apparaît en grand.
- Le guide rassemble Espace, Connexions, Outils et Bienvenue. Les liens vers
  les outils et les réglages suivent la navigation autorisée du backend.
- Les accès métier restent protégés par les API et le contrôle d’abonnement.
- Aucun dossier Drive, projet, client ou événement n’est créé par le guide.
  Les liens de configuration ouvrent les réglages existants.
- Le guide est une aide de navigation, pas un chatbot ni une source de réponses
  générées. Les anciennes promesses de collecte automatique sont retirées de
  l’écran de bienvenue au profit des usages actuels de Radar.

## Visage et mouvement

Deux yeux, leurs reflets et une bouche fine, sans membres ni contour ajouté.
Une surface dégradée et un reflet donnent du volume à la sphère. Couleurs :
cyan au repos, orange en curiosité et jaune pour l’étape des outils.

La respiration et la lumière utilisent CSS. Au repos, des délais irréguliers
pilotent clignements, regards, air rêveur, bâillement et clin d’œil. Un curseur
proche attire les yeux et réveille l’expression ; le focus clavier apporte la
même attention. Les changements d’étape réveillent brièvement la sphère.

Les coordonnées du pointeur ne sont ni stockées ni envoyées. Leur traitement
est plafonné à un requestAnimationFrame à la fois et met à jour une translation
CSS, sans nouvelle requête ni rendu React à chaque mouvement.

## Accessibilité et cycle de vie

- Le visage est décoratif et masqué aux lecteurs d’écran. Le bouton d’aide
  possède un nom explicite et le dialogue un titre et une description.
- Tabulation, Échap, fermeture et retour du focus fonctionnent via Radix.
- Les expressions ne sont pas des annonces live qui interrompent la lecture.
- Le mouvement réduit supprime respiration, transitions et minuteries du visage.
- Les minuteries et le suivi du pointeur sont arrêtés lorsque la sphère est
  inactive, hors de l’écran ou dans un onglet masqué. Les écouteurs, observateurs
  et minuteries sont nettoyés au démontage.
- La sphère de la barre se met en pause derrière le guide ouvert.

Le choix de fermeture du guide utilise la clé de préférence déjà existante
`opportunities-radar-welcome-shown-v2`. Les utilisateurs ayant déjà passé
l’accueil ne subissent pas de nouvelle ouverture automatique. Le guide reste
accessible à tout moment via la mascotte.

## Vérification et déploiement

`scripts/mascot_ui_smoke.py` utilise une instance locale et des réponses API
explicitement simulées : veille/clignements, micro-expressions, regard,
focalisation, guide selon les droits, pause en mouvement réduit/onglet masqué,
fermeture et persistance de la préférence. Les horloges Playwright avancent les
minuteries sans introduire de mode de test dans le composant de production.

Le changement est frontend uniquement : pas de migration ni de configuration
fournisseur. Construire et recréer le frontend à partir de la branche dédiée.
La branche repose sur le nettoyage technique précédent.
