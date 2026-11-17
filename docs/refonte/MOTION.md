# Animations Radar

Le mouvement complète la DA claire et violette, avec des interactions courtes :

- fondu de 220 ms à la navigation, sans remonter le composant de page ;
- barre latérale et contenu synchronisés sur 220 ms ;
- pression des boutons, apparition des cartes et panneaux d’onglets ;
- panneaux mobiles ouverts en 200 ms et fermés en 150 ms ;
- apparition au défilement des sections publiques (380 ms, une fois par section) ;
- balayage décoratif du radar à l’arrivée, sans boucle ni données simulées.

Les contenus ne sont jamais masqués en attendant JavaScript ou un observateur.
Les animations Web Animations sont annulées à la navigation, au démontage et
quand le réglage système « réduire les animations » est activé. L’observateur
est déconnecté et ne surveille ni les tableaux, ni les cartes géographiques,
ni les éléments glissables. Les animations de page ne changent pas le DOM des
formulaires et ne transforment pas le parent des menus fixes.

Les animations CSS ajoutées sont supprimées en mouvement réduit et à l’impression.
Le défilement devient immédiat en mouvement réduit. MotionConfig transmet la
préférence système aux composants Framer Motion existants. Aucun paquet ajouté.

Validation : `npm run type-check`, `npm run build`, puis, avec un frontend local
de production et Playwright, `python scripts/motion_ui_smoke.py` et
`python scripts/ui_smoke.py`. Le test motion couvre ordinateur/mobile, mouvement
normal/réduit, modification du réglage sans perte des champs, fermeture clavier
du menu, erreur de connexion explicite et contenu visible sans JavaScript.
Les réponses API de ces tests navigateur sont des fixtures explicites ; aucun
appel fournisseur réel n’est validé. Le test motion est inclus dans la CI.

Aucune migration, clé API ni configuration backend requise. La livraison de
ces changements nécessite la reconstruction de l’image frontend du VPS.
