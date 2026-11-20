# Journal d’activité super-admin

La page `/admin/activity` présente les événements effectivement enregistrés par
Radar. Elle n’est pas un inventaire exhaustif des requêtes HTTP, des traitements
externes ou des événements d’infrastructure. L’absence de ligne ne prouve pas
qu’une opération n’a jamais eu lieu.

## Consultation

- Recherche par nom, e-mail, action technique, identifiant de suivi ou ressource.
- Filtres par auteur, action, type de ressource et période ; appliquer explicitement.
- Dates personnalisées et affichage en Europe/Paris, y compris les changements d’heure.
- Pagination de 25 événements ; synthèse calculée sur tous les résultats filtrés.
- Détail : auteur, date, action technique, ressource, adresse IP et informations enregistrées.
- Actualisation manuelle ou toutes les 30 secondes, désactivée par défaut et en
  pause sur les pages suivantes. L’heure affichée est celle du dernier chargement réussi.
- Une erreur de rafraîchissement conserve les résultats précédents et signale leur ancienneté.

## API et données

`GET /api/v1/admin/logs/search` renvoie `items`, `total`, `page`, `limit` et
`summary` (nombre d’auteurs identifiés, connexions et dernier événement).
`GET /api/v1/admin/logs/filters` fournit les options issues des événements existants.
Les anciennes routes logs, stream, stats et users/tracking restent disponibles.
Toutes exigent le drapeau de super-administrateur de plateforme : un rôle
administrateur d’agence seul ne suffit pas.

L’auteur est joint à la requête, sans requête utilisateur supplémentaire par ligne.
Les secrets identifiables (mots de passe, jetons, codes A2F et paramètres sensibles
d’URL) sont masqués à la lecture des détails dans les anciennes et nouvelles routes.
Les détails volumineux sont tronqués dans cette projection. Les enregistrements
originaux restent inchangés en base ; aucune migration ni purge n’est nécessaire.
Cette protection ne remplace pas l’obligation de ne jamais journaliser de secrets.
La rétention des journaux n’est pas modifiée par ce rework.

## Vérification

Tests PostgreSQL : droits, filtres, pagination et synthèse cohérentes, changement
d’heure, rejet des paramètres invalides, masquage sans modification de l’original
et nombre de requêtes borné. Scénarios navigateur sur fixtures locales : erreurs,
reprise, détails, pagination, dates, états vides et absence de débordement en
1440, 390 et 320 px, thèmes clair et sombre. Le scénario est intégré à la CI.
