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

Le bouton ouvre une aide contextuelle. Son action « Revoir les premiers pas » ouvre le guide en plein écran, avec fermeture explicite, touche Échap, focus contenu dans le dialogue et restitution du focus au bouton d’aide. Les contenus entrent et sortent avec un fondu et un léger déplacement ; la préférence de réduction des animations désactive ces mouvements. L’écran central peut défiler sur mobile et les commandes restent accessibles en bas.

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

## Aide contextuelle et réactions aux actions

Le clic sur la mascotte ouvre maintenant un panneau d’aide adapté à la route autorisée : projets, tâches, calendrier, fichiers, Discovery, événements, clients, devis, factures et réglages. Le texte provient des articles de documentation existants ; le lien « Lire le guide complet » pointe vers l’article public correspondant. Une route inconnue ou indisponible utilise les premiers repères généraux. Le panneau ne modifie aucune donnée. « Revoir les premiers pas » ouvre le guide plein écran une fois le panneau fermé. Les deux dialogues et l’accueil automatique sont mutuellement exclusifs ; Échap et la restitution du focus sont conservés.

`useRadarReaction` observe uniquement les identifiants et types des nouvelles notifications existantes (ToastProvider et Sonner), jamais leurs titres, descriptions, données de formulaire ou réponses API. Une confirmation donne l’expression satisfaite ; une erreur, l’expression déçue ; un avertissement ou une validation HTML invalide, l’expression intriguée. Ce sont des réactions visuelles aux retours existants : elles ne remplacent pas le message de résultat. Une confirmation d’analyse lancée ne signifie pas que l’enrichissement est terminé.

Les réactions durent trois secondes, ne se rejouent pas lors d’un rendu, et sont annulées à un changement de route/workspace, à l’ouverture de l’aide ou au masquage de l’onglet. Les anciennes notifications présentes au montage sont ignorées. Il n’y a ni stockage de ces réactions, ni collecte, ni nouvel appel réseau. Les préférences de mouvement réduit continuent de s’appliquer au visage.

Les pages métier utilisaient déjà Sonner sans conteneur d’affichage global : un conteneur unique affiche désormais ces notifications et suit le thème courant. La création et la modification des projets, qui ne signalaient pas leurs résultats, émettent maintenant une confirmation seulement après une réponse API positive, ou une erreur explicite en cas d’échec en conservant le formulaire. Le visage décoratif ne capture pas les clics : les glyphes peuvent changer pendant le survol sans interrompre l’ouverture de l’aide.

`scripts/companion_ui_smoke.py` vérifie l’aide sur ordinateur/mobile, l’absence d’écriture pendant sa consultation, une sauvegarde retardée puis confirmée (201), un refus réel (403), la validation HTML sans requête, la notification Sonner d’une analyse mise en attente et le repli général d’une page non incluse dans Core. Ces scénarios utilisent uniquement des fixtures locales.
