# Audit complémentaire des API — 20 octobre 2026

Inventaire exportable : [API-INVENTORY.csv](API-INVENTORY.csv), régénérable avec `PYTHONPATH=backend python scripts/api_inventory.py docs/refonte/API-INVENTORY.csv`. La colonne de sécurité décrit OpenAPI, pas une preuve de contrôle effectif.

Périmètre : contrats OpenAPI (485 opérations sur 382 chemins), routage, authentification HTTP/temps réel, suivi de tâches, annotations d’opportunités et recherche de contacts. L’inventaire statique ne constitue pas un test fonctionnel de chacune des 485 opérations. Les intégrations externes ne sont pas déclarées validées sur cette base.

## Défauts confirmés et correctifs

| Défaut | Effet | Correction |
|---|---|---|
| SSE sans sélection obligatoire ni propriété des jobs | Écoute possible du canal partagé de progression | Sélection obligatoire, maximum 20 jobs ; propriété utilisateur + workspace enregistrée avant dispatch Redis avec expiration 24h ; refus des jobs inconnus/hérités |
| Authentification EventSource incohérente avec les dépendances HTTP | Le frontend utilisait un token URL alors que le routeur imposait un header | Dépendance spécifique SSE, compte actif et appartenance contrôlés ; header privilégié lorsqu’il est présent, query conservée pour EventSource |
| WebSocket vérifiant seulement la signature JWT | Comptes supprimés/désactivés admis | Vérification du compte en base avant ouverture |
| Jeton 2FA en attente accepté comme accès | Contournement du second facteur | Refus central des jetons `2fa_pending` ; vérification 2FA séparée authentifiée et limitée au compte courant |
| Sujet JWT signé non numérique | Erreur SQL plutôt qu’un refus d’authentification | Identifiant entier positif borné avant requête |
| Tags/favoris sans workspace ORM | Annotations du même utilisateur exposées dans ses autres workspaces ; créations incompatibles avec colonnes existantes | Mapping des colonnes déjà créées par 028 ; écriture du workspace et filtrage des commentaires par opportunité |
| Tags personnalisés branchés sur les tags historiques ; `len()` sur relation dynamique | Ajout/liste en erreur | Relation personnalisée correcte et décompte SQL |
| Résultats de recherche de contacts sans filtrage du parent | Accès par identifiant à un résultat d’une autre agence | Filtrage par opportunité et workspace |
| Redirections du crawler suivies après validation de la seule URL initiale | Contournement possible de la protection contre les requêtes internes | Redirections bloquées, validation de chaque URL, refus credentials/ports non HTTP, limite 2 Mo décompressés/page |
| Identifiants UUID/int incompatibles | Routes sources/contact et réponses collection en erreur | Contrats alignés sur les modèles réels |
| Routes sources et rapports enregistrées deux fois | OpenAPI différent de l’exécution ; route `/sources/health` masquée | Routeurs canoniques, helpers historiques conservés hors routage, chemins statiques prioritaires ; zéro operationId dupliqué |
| Vérification de santé détaillée annoncée protégée mais sans dépendance | Exposition de l’état des services et import invalide | Accès plateforme, clients Redis bornés et fermés, session injectée |
| Collectes historiques sans propriétaire de workspace | Consultation des runs entre agences | Migration additive 050, nouveaux runs attribués, runs historiques non attribués conservés mais masqués ; workers refusant les runs non attribués |
| Syntaxe de fixture compatible seulement avec Python 3.12 | Échec pytest en CI Python 3.11 | F-string compatible 3.11 ; analyse syntaxique de tous les fichiers backend |

Les signatures `regex=` obsolètes de FastAPI ont été remplacées par `pattern=` en conservant leurs expressions.

## Migration 050

Ajoute `collection_runs.workspace_id`, nullable, une clé étrangère et un index. Aucune attribution arbitraire des anciens runs : leur restitution nécessite un rapprochement administratif fiable avec les entités/commanditaires. Aucun run n’est effacé. Downgrade automatique possible tant qu’aucune attribution n’a été enregistrée ; ensuite refus explicite pour préserver cette information de sécurité.

Les champs workspace de tags/favoris existent dans la migration 028 : leur ajout au mapping ORM ne nécessite pas de migration de schéma supplémentaire. Les bases qui n’ont pas appliqué cet historique doivent être rapprochées du schéma avant déploiement.

## Limites et suites

- La chaîne Alembic historique reste bloquée avant les migrations nouvelles ; voir MIGRATIONS.md. Aucune dépendance historique n’a été réécrite.
- La protection SSRF n’épingle pas encore la connexion à l’adresse DNS validée : une restriction d’egress réseau reste nécessaire contre le rebinding DNS.
- Le jeton EventSource reste dans l’URL ; masquer les query strings dans les journaux des proxies. Un remplacement par tickets courts nécessite une évolution coordonnée du protocole.
- Redis ne constitue pas un registre commercial durable des tâches ; perte/expiration des clés => refus sûr de consulter la progression, sans suppression du run métier.
- Authentification temps réel contrôlée à l’ouverture ; révocation immédiate d’une connexion déjà ouverte non implémentée. Diffusion globale WebSocket à réserver aux messages sans données d’agence.
- Les workers historiques de collecte et les mappings de documents/contacts doivent encore être confrontés à une copie anonymisée du schéma déployé : l’historique 028 ajoute des champs que certains anciens chemins d’écriture ne renseignent pas. Leur simple présence ne signifie pas que l’ingestion réelle fonctionne.
- Tests de fournisseurs Google/Spotify/Deezer, paiements et envoi d’emails hors périmètre de validation locale sans comptes de test dédiés.
