# Radar — Direction artistique « Signal clair »

## Intention

Radar donne à une agence un point de repère commun. La marque évoque la détection, la perspective et le passage à l’action. Sa présentation reste calme : les données et les tâches occupent le premier plan, les motifs de marque servent à orienter.

## Identité

Le sigle associe des cercles concentriques, un centre et un signal placé sur une direction. Le mot-symbole **Radar.** utilise une chasse resserrée. Le composant `RadarLogo` est commun à la vitrine, la connexion, l’espace agence, l’administration et aux documents légaux. `RadarMark` fournit le sigle seul ; le favicon reprend sa géométrie. La variante inversée sert aux surfaces sombres.

Les cercles et les repères sont des illustrations décoratives : ils ne représentent ni une audience, ni une performance mesurée. Pas de balayage animé permanent derrière les tableaux et les formulaires.

## Couleurs et typographie

| Rôle | Référence | Usage |
| --- | --- | --- |
| Violet signal | `--primary: 253 66% 59%` | Actions principales, navigation active, repères et liens |
| Encre | `--foreground: 237 24% 16%` | Titres et texte principal |
| Fond clair | `--background: 240 20% 98%` | Plan de travail |
| Blanc | `--card` | Cartes, champs et surfaces de lecture |
| Gris secondaire | `--muted-foreground` | Contexte et informations secondaires |
| Vert, ambre, rouge | Tokens existants | Inclusion/validation, attention et erreur, selon le sens métier |

Inter reste la police du produit, chargée par `next/font`. Les grands titres ont un interlettrage resserré ; les libellés restent sobres. Les nombres des tableaux utilisent des chiffres tabulaires. Les majuscules espacées sont réservées aux repères de section courts.

Les tokens et motifs résident dans `frontend/src/app/radar-brand.css`. Les composants conservent les variantes sémantiques existantes, notamment les statuts d’erreur et les actions destructrices.

## Déclinaison

- **Vitrine** : présentation des quatre domaines, illustration orbitale sans chiffres de démonstration, parcours « repérer / structurer / avancer », offres issues du catalogue API et appel au contact. L’ancienne maquette de dashboard et les arguments concernant banque ou veille suspendues ne sont plus utilisés sur l’accueil. Leurs composants sources sont conservés.
- **Pages publiques** : en-tête, navigation mobile, pied de page, abonnements, contact et repères de marque des documents légaux harmonisés. Le contenu juridique reste inchangé.
- **Connexion et accès** : sigle commun, composition à deux colonnes sur ordinateur, formulaire prioritaire sur téléphone, mêmes formulaires email et 2FA. L’attente d’invitation et la configuration initiale utilisent les mêmes surfaces.
- **Application** : logo et tokens communs ; titres, espacements, tableaux, champs, navigation et surfaces partagés. Adaptations des projets, production, fichiers, clients, pipeline, inbox, devis, factures, calendrier, comparaison, Discovery et paramètres. Les composants communs déclinent la DA sur les autres écrans et fiches.
- **Administration** : même marque en version inversée, sans modification du contrôle des droits.

## Règles produit

Les couleurs d’une plateforme externe et les statuts métier ne sont pas remplacés arbitrairement par du violet. Aucune donnée fictive n’est ajoutée aux écrans réels. Les abonnements conservent leurs droits backend et aucun prix n’est créé. Les API, modèles, comptes, workspaces et migrations ne sont pas modifiés par ce lot.

## Mise à jour du Codespace

Sur la branche de travail, récupérer les modifications avec `git pull --ff-only`, puis actualiser Radar. Le serveur de développement recharge les styles et composants ; les données de test sont conservées.

## Validation de ce lot

Le typage TypeScript et le build Next.js passent. Les contrôles navigateur couvrent 21 visites publiques (accueil, abonnements, contact, documents légaux et connexion à 1440, 768 et 390 px), cinq scénarios d’application sur Core/Premium/Business et deux régressions de fiches artistes. Les menus, liens, affichages d’offres, demandes Addons, connexion refusée, Google configuré/non configuré et absence de débordement horizontal sont vérifiés. Les captures ont servi à corriger le placement des motifs et l’interlignage.

Les API de ces essais sont des fixtures explicites. Ils valident le rendu et les interactions frontend, sans prétendre à une nouvelle validation des fournisseurs externes, paiements ou migrations. Aucune base de production n’a été utilisée.
