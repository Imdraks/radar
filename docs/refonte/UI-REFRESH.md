# Interface claire et accents violets

La mise à jour conserve les routes, les données et les contrôles d’accès existants. Elle harmonise la présentation du produit autour d’un thème clair, de surfaces blanches et d’accents violets.

## Changements

- Navigation commune : icônes, sections plus lisibles, sélection active sur les sous-pages, contexte de navigation dans l’en-tête, identité du workspace et compte utilisateur. Les entrées proviennent toujours de la navigation renvoyée par le backend.
- Barre latérale affinée : panneau de 280 px, fond légèrement violet, sections séparées, icônes encadrées sur la page active et repère violet. Le menu défile indépendamment du compte et de l’abonnement fixés en bas ; les sections vides ne sont pas affichées. Le même dessin est utilisé dans le tiroir mobile.
- Mobile : tiroir réutilisant le composant Radix existant pour le focus, Échap et le retour au bouton d’ouverture ; accès rapides avec icônes et état actif. Le tiroir se ferme au passage en affichage desktop.
- Composants communs : boutons, cartes, champs et couleurs harmonisés ; suppression du chargement Google Fonts redondant avec `next/font`. Les champs natifs des formulaires de l’application bénéficient d’un fond et d’un focus explicites.
- Accueil : suppression du double espacement, en-tête responsive, salut utilisant le nom réel de l’utilisateur et indicateurs placés avant les détails. Les chiffres continuent de provenir de l’API.
- Abonnement : synthèse de l’offre actuelle, cartes comparables, offres couvertes affichées « Déjà inclus » en vert, demandes pour les offres supérieures, formulaire Addons lisible avec état d’envoi. Les demandes commerciales conservent les mêmes API et ne changent pas directement les droits.
- Événements : surfaces et formulaire harmonisés avec les composants communs.

La structure de chaque écran métier n’est pas entièrement réécrite : les pages utilisent la nouvelle navigation et les styles communs ; les adaptations spécifiques portent sur l’accueil, l’abonnement et le formulaire événementiel. Le choix de thème sombre existant reste disponible.

## Validation

Le typage TypeScript et le build de production passent. `scripts/ui_smoke.py` vérifie les trois plans sur ordinateur (1440 px), puis Business sur tablette (768 px) et téléphone (390 px) : offres incluses en vert, demandes commerciales, formulaire Addons, accueil, erreur événement explicite, ouverture/fermeture du menu au clavier et absence de débordement horizontal. Les cinq scénarios passent sans erreur JavaScript. La régression `scripts/social_ui_smoke.py` passe aussi à 1440 et 390 px, y compris l’enregistrement des profils et le rafraîchissement après enrichissement.

Ces essais navigateur utilisent des API simulées et explicitement identifiées comme tests. Ils vérifient l’interface et ses requêtes ; ils ne constituent pas une nouvelle validation des fournisseurs externes ni des paiements. Aucun changement backend ou migration n’est nécessaire pour ce lot.

## Voir la mise à jour dans un Codespace existant

Dans le terminal du Codespace, sur la branche `refactor/radar-product-security` :

```sh
git switch refactor/radar-product-security
git pull --ff-only
```

Le serveur Next.js de développement recharge les fichiers modifiés. Actualiser ensuite la page Radar. Si Git signale des modifications locales incompatibles, les conserver et résoudre le conflit ; aucune réinitialisation destructive n’est nécessaire. Aucun changement du schéma de données ni reconstruction du Codespace n’est requis pour ce lot.
