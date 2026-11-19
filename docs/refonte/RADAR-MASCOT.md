# Radar — visage typographique et guide immersif

## Composition

`frontend/src/components/mascot/RadarFace.tsx` compose le visage avec de vrais caractères héritant de la police Inter déjà chargée par Next.js : parenthèses tournées pour les sourcils, points `•` pour les yeux et la bouche, `o`, `)` et `–` pour les expressions. Chaque partie possède son élément DOM et ses transformations CSS. Aucun SVG, canvas, image, sprite ou service de génération ne constitue le visage.

Le fond reste transparent. Le visage reprend la couleur du texte, y compris dans le thème sombre. Les états calme, curieux et idée agissent sur l’expression, sans ajouter une sphère ou un contour.

## Mouvement

- Regards spontanés, clignements irréguliers, rêverie, bâillement et clin d’œil.
- Réaction au survol proche et au focus clavier. Le regard suit le pointeur à proximité, avec une amplitude bornée.
- Les déplacements sont des variables CSS relatives à la taille du visage. Le pointeur ne provoque pas un rendu React à chaque mouvement.
- Suspension quand le guide masque le bouton d’aide, quand le visage sort du viewport, quand l’onglet est masqué, ou si `prefers-reduced-motion` est actif.
- Nettoyage des timers, observateurs, écouteurs et frames au démontage.
- Aucun enregistrement des mouvements, aucune requête externe.

## Intégration

Le visage remplace le bouton d’aide existant dans l’en-tête de l’espace de travail. Son nom accessible est « Ouvrir l’aide Radar ». Le visage est décoratif pour les lecteurs d’écran.

Le bouton ouvre un guide en plein écran, avec fermeture explicite, touche Échap, focus contenu dans le dialogue et restitution du focus au bouton d’aide. Les contenus entrent et sortent avec un fondu et un léger déplacement ; la préférence de réduction des animations désactive ces mouvements. L’écran central peut défiler sur mobile et les commandes restent accessibles en bas.

Les quatre étapes présentent :

1. L’espace de travail réel.
2. Les connexions disponibles, avec un lien de configuration réservé aux accès appropriés.
3. Les outils accessibles selon la navigation renvoyée par le backend.
4. Les repères pour commencer et un lien vers la documentation.

Le guide ne crée pas de dossier Google Drive, ne confirme pas de connexion inexistante et ne modifie pas les droits. Les accès backend restent souverains.

Le guide de première visite conserve la préférence existante `opportunities-radar-welcome-shown-v2`. Un utilisateur déjà accueilli peut ouvrir le guide manuellement. La fermeture ne déclenche aucune mutation API ; elle enregistre uniquement les préférences locales existantes du guide.

## Validation et déploiement

`scripts/mascot_ui_smoke.py` utilise des réponses API de test explicitement locales pour vérifier les animations, les glyphes Inter, le plein écran, la navigation clavier, les permissions Core/Business, l’absence de mutation, le mouvement réduit et la fermeture persistante. Il fait partie des contrôles frontend de la CI.

Modification frontend uniquement : pas de migration ni de clé supplémentaire. Reconstruire et recréer le service `frontend` avec les deux fichiers Compose du VPS. Le déploiement sur le VPS reste une opération distincte des tests locaux.
