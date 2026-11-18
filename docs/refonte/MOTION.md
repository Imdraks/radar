# Animations Radar

Le mouvement complète la DA claire et violette, avec des interactions courtes :

- fondu de 280 ms à la navigation et léger mouvement du titre sur 320 ms,
  sans remonter le composant de page ;
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

Les transitions de route ne s’exécutent qu’aux changements de chemin, y compris
le retour navigateur. Un observateur court attend un contenu monté tardivement
ou la fin de `aria-busy` sur le conteneur de l’application. Il est arrêté dès
que le contenu est animé, au changement de route, au démontage ou après huit
secondes. Aucun lien n’est intercepté, aucune navigation retardée et aucun
instantané de l’ancien écran conservé. Le chargement initial, les paramètres de
filtre et les ancres ne provoquent pas de nouveau fondu global.

`scripts/route_transition_ui_smoke.py` couvre navigation cliente/retour, contenu
protégé retardé, mouvement réduit, conservation des champs et coordonnées des
fenêtres fixes ; API locales simulées et aucune connexion client réelle.

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
