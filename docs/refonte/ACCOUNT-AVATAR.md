# Compte connecté dans l’en-tête public

L’en-tête public remplace les boutons de connexion/contact par le compte lorsqu’une
session est vérifiée par `GET /api/v1/auth/me`. La présence d’un jeton ou le contenu
persisté dans Zustand ne suffisent pas. Une session refusée laisse le visiteur sur
la page publique ; aucun renvoi automatique vers la connexion.

Le menu donne accès à l’espace, aux paramètres et à la déconnexion existante.
Il fonctionne sur ordinateur et mobile, avec le clavier et le focus Radix.

## Photo et niveaux visuels

- La photo Google déjà enregistrée est utilisée par défaut, sans nouvel appel OAuth.
- Une photo personnalisée peut la remplacer dans Paramètres > Compte.
- Retirer la photo personnalisée rétablit la photo de connexion si elle existe.
- Une image indisponible affiche les initiales ; aucune photo fictive n’est affichée.
- Les images distantes sont chargées avec `referrerPolicy="no-referrer"`.
- Contour violet épais, liseré blanc et arcs extérieurs décoratifs.
- Le même style fixe est appliqué à tous les abonnements, sans animation.

Le nom d’abonnement du menu provient du workspace sélectionné et de l’API
authentifiée. Si l’abonnement ne peut pas être lu, le menu invite à le consulter.
L’apparence de l’avatar est indépendante de cette information. Les contours
sont décoratifs et n’attribuent aucun droit.

## Import et conservation

`POST /api/v1/auth/me/avatar` accepte un fichier multipart nommé `file`.
`DELETE /api/v1/auth/me/avatar` retire uniquement la photo personnalisée.
Ces routes ciblent exclusivement l’utilisateur authentifié et n’acceptent pas
l’identifiant d’un compte à modifier.

Le serveur limite le contenu à 2 Mio et l’image décodée à 4 millions de pixels.
JPEG, PNG et WebP sont décodés puis réencodés par Pillow en JPEG carré de 256 px,
sans métadonnées, avec un maximum de 64 Kio. Les SVG et fichiers invalides sont
refusés. Les contrôles du navigateur ne remplacent pas cette validation.

La miniature est stockée dans PostgreSQL, sans stockage disque additionnel ni
nouvelle configuration fournisseur. Elle est chargée à la demande plutôt qu’à
chaque authentification d’une requête métier. L’API de compte renvoie la miniature
comme URI de données dans `avatar_url`, ou l’URL SSO d’origine. Les réponses d’auth
restent `no-store`. L’export personnel inclut `profile_avatar_url`.

## Migration et déploiement

`059_profile_avatar` ajoute une colonne binaire nullable `users.avatar_image`.
Les utilisateurs et les URL Google existantes sont conservés. Aucune donnée
existante n’est migrée ou supprimée.

Construire le backend et le frontend, sauvegarder PostgreSQL, exécuter
`alembic upgrade head` avec la nouvelle image puis recréer backend, worker,
scheduler et frontend. Le connecteur MCP et les volumes restent en place.

Le downgrade vers 058 fonctionne si aucune photo personnalisée n’est enregistrée.
Sinon il refuse explicitement de supprimer la colonne : exporter les miniatures
et décider de leur traitement avant de relancer le downgrade. L’ancienne image
applicative peut lire la base conservant cette colonne nullable supplémentaire.

## Vérification

- Tests backend : vrais jetons, stockage PostgreSQL jetable, isolation des comptes,
  authentification, import/retrait, préservation SSO, métadonnées et limites.
- Historique des migrations : installation et mises à niveau, rollback propre,
  refus de perte des photos déjà enregistrées.
- `scripts/public_account_ui_smoke.py` : données API explicitement simulées,
  visiteurs et sessions refusées/renouvelées, tiers et expiration, image cassée,
  menu clavier/mobile, mouvement réduit et import/retrait dans les paramètres.
