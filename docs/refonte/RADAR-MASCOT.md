# Radar — visage typographique et guide immersif

## Composition

`frontend/src/components/mascot/RadarFace.tsx` compose le visage avec de vrais caractères héritant de la police Inter déjà chargée par Next.js : parenthèses tournées pour les sourcils, points `.` pleins pour les yeux ronds et tiret `-` pour la bouche neutre. Les sourcils neutres restent au même niveau ; aucune bouche ronde ni expression surprise n’est imposée à l’ouverture. Chaque partie possède son élément DOM et ses transformations CSS. Aucun SVG, canvas, image, sprite ou service de génération ne constitue le visage.

Le fond reste transparent. Le visage reprend la couleur du texte, y compris dans le thème sombre. Le catalogue `expressions.ts` contient les 44 expressions demandées. La propriété typée `expression` permet de choisir chacune explicitement, sans que le survol ou le clignement automatique ne la remplace. Les grands yeux `O` / `0` deviennent des points pleins plus grands ; les autres signes restent des caractères Inter. La bouche de « FOU », absente de la liste fournie, utilise un tiret neutre. Aucun effet de sphère ou contour n’est ajouté.

## Mouvement

- Regards spontanés, clignements irréguliers, sourire, satisfaction, somnolence, bâillement et clin d’œil. Les états négatifs et « argent » ne sont jamais sélectionnés aléatoirement au repos.
- Sourire au survol proche et au focus clavier, puis retour au neutre. Le regard suit le pointeur à proximité, avec une amplitude bornée.
- Les déplacements sont des variables CSS relatives à la taille du visage. Le pointeur ne provoque pas un rendu React à chaque mouvement. Le groupe des yeux possède ses propres micro-déplacements irréguliers ; la bouche reste fixe. Une courte transition CSS accompagne les changements d’expression.
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

`node scripts/mascot-expressions.test.mjs` vérifie le rendu des 44 expressions et le contrat du visage neutre.

`scripts/mascot_ui_smoke.py` utilise des réponses API de test explicitement locales pour vérifier les animations, les glyphes Inter, le plein écran, la navigation clavier, les permissions Core/Business, l’absence de mutation, le mouvement réduit et la fermeture persistante. Il fait partie des contrôles frontend de la CI.

Modification frontend uniquement : pas de migration ni de clé supplémentaire. Reconstruire et recréer le service `frontend` avec les deux fichiers Compose du VPS. Le déploiement sur le VPS reste une opération distincte des tests locaux.

## Référence de mouvement

[Blobstudio](https://github.com/aivsomkar/blobstudio), notamment les sections « Eye life » et « The gaze fix » du README, a servi de référence pour séparer la forme de l’expression du regard, centrer le repos et donner aux yeux de petits mouvements indépendants. Radar conserve son propre rendu de caractères DOM et ses propres temporisations/transitions CSS. Aucun moteur SVG, donnée d’expression ou code tiers de Blobstudio n’est embarqué ; aucune dépendance ajoutée.
