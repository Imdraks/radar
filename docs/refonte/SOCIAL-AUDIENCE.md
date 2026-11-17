# Instagram, TikTok et YouTube : compteurs publics

## Résultat des vérifications réelles du 20 octobre 2026

| Plateforme / profil | Résultat observé | Précision et limite |
|---|---|---|
| [Instagram — Billie Eilish](https://www.instagram.com/billieeilish/) | `124M` abonnés, vers 09:12 UTC | Affichage public arrondi ; normalisé à 124 000 000 pour les calculs, accompagné de `rounded_public_display` et du texte original. Ce n’est pas une mesure exacte à l’unité. |
| [Instagram — Dua Lipa](https://www.instagram.com/dualipa/) | `89M`, vers 09:12 UTC | Même distinction entre affichage arrondi et valeur normalisée. |
| [TikTok — Billie Eilish](https://www.tiktok.com/@billieeilish) | `74700000`, vers 09:12 UTC | Entier publié dans `userInfo.stats.followerCount`. Aucune garantie supplémentaire de précision interne de TikTok. |
| [TikTok — Dua Lipa](https://www.tiktok.com/@dualipa) | Donnée indisponible | Le payload renvoie un code non nul avec des compteurs zéro de remplacement. Ces zéros sont rejetés. |
| YouTube — pages publiques | Validation bloquée dans cet environnement | Le proxy refuse les connexions au domaine YouTube avec `403 Forbidden`. Aucun contournement ni proxy tiers employé. |
| YouTube — API officielle | Connecteur préparé et testé sur fixtures ; pas de collecte réelle validée | Nécessite `YOUTUBE_API_KEY`. Aucune clé configurée lors des essais. |

Ces chiffres sont des observations datées de test, pas des constantes intégrées au produit. Les profils ci-dessus servent uniquement à vérifier les collecteurs ; ils ne sont pas ajoutés aux workspaces clients.

## Méthodes gratuites

### Instagram

Lecture HTTP de la page publique, vérification de l’identité `@handle` dans les métadonnées de profil, puis extraction du compteur affiché dans `og:description`. Les pages de connexion, profils sans compteur et identités différentes restent indisponibles. Aucune API privée ni session Instagram empruntée. La source publique peut changer ou limiter l’accès.

Pour un compteur autorisé via API, l’option officielle [Meta Business Discovery](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) concerne des comptes professionnels et requiert la configuration Meta/les permissions adaptées. Ce connecteur authentifié n’est pas inclus dans ce lot, et aucun chiffre exact supplémentaire n’est promis.

### TikTok

Lecture du JSON `__UNIVERSAL_DATA_FOR_REHYDRATION__`, uniquement à la clé `__DEFAULT_SCOPE__["webapp.user-detail"].userInfo`. Le code de réponse doit être zéro, `user.uniqueId` doit correspondre au profil demandé, et `stats.followerCount` doit être un entier non négatif. Les recommandations, likes et codes d’erreur ne sont jamais utilisés comme nombre d’abonnés.

L’[API Display officielle](https://developers.tiktok.com/docs/en/tiktok-api-v2-get-user-info) expose aussi les statistiques via `user.info.stats`, avec autorisation du compte concerné. Cette alternative OAuth n’est pas configurée ici.

### YouTube

Connecteur de l’[API YouTube Data v3, channels.list](https://developers.google.com/youtube/data/reference/rest/v3/channels/list), par identifiant de chaîne ou handle explicite. Cette méthode consomme une unité de quota par requête et peut être utilisée dans le quota gratuit du projet Google Cloud ; aucun service de scraping payant ajouté. Les compteurs publics restent [arrondis à trois chiffres significatifs](https://developers.google.com/youtube/data/reference/rest/v3/channels#statistics.subscriberCount), même quand l’API retourne une chaîne de chiffres entière.

À configurer par l’exploitant : activer YouTube Data API v3 dans son projet Google Cloud, créer/restreindre une clé à cette API puis renseigner `YOUTUBE_API_KEY` dans l’environnement du backend et des workers. Les fichiers Compose existants chargent `.env`. Redémarrer les services concernés. La clé reste côté serveur, transmise dans un header Google, jamais dans une URL, un snapshot ou une variable frontend `NEXT_PUBLIC_`. Aucun projet Cloud, paiement ou clé n’a été créé automatiquement.

Sans clé, le résultat porte `configuration_required / YOUTUBE_API_KEY_REQUIRED`. Un nombre d’abonnés masqué ou une réponse correspondant à une autre chaîne reste indisponible. Cette voie doit encore être validée avec une vraie clé autorisée ; les tests de fixtures ne prouvent pas une intégration opérationnelle.

## Intégration produit

- Les liens explicites publiés dans la fiche Spotify de l’artiste peuvent alimenter les profils associés, après validation des domaines et chemins. Aucun pseudonyme n’est deviné à partir du nom d’artiste.
- La fiche Discovery permet d’associer/corriger les trois URL. La sauvegarde est contrôlée par workspace, rôle d’écriture et abonnement Premium/Business. Le bouton d’enrichissement existant déclenche les collectes.
- Cache public de 12 h, cache d’échec de 15 min, délai de connexion/lecture borné et réponse limitée à 2 Mo. Un 429 suspend les requêtes vers la plateforme et respecte au minimum le délai `Retry-After` numérique reçu. Aucune redirection suivie vers un site arbitraire.
- Provenance par plateforme dans un snapshot `SOCIAL` : valeur, affichage original, statut, précision, URL et date effective de collecte. La date du cache est préservée ; une tentative échouée ne reçoit pas une fausse date de collecte.
- Les données tierces Viberate déjà disponibles restent réutilisables avec une provenance distincte et une précision explicitement inconnue ; elles ne sont pas attribuées à une collecte directe réussie.
- Changer un profil masque la valeur liée à l’ancien profil dans la fiche jusqu’au prochain enrichissement. Les observations historiques restent conservées.
- Les abonnés manquants restent `null`, les zéros réellement publiés sont conservés. Les fans Deezer ne sont plus substitués aux abonnés Spotify ni au total des autres réseaux dans ce calcul.
- Pas de nouvelle migration SQL : réutilisation des champs URL et snapshots JSON existants. Les variantes de parser/cache Spotify changent pour récupérer ses liens explicites lors du prochain enrichissement.

## Reproduire sans service payant

```bash
PYTHONPATH=backend .venv/bin/python scripts/social_followers.py \
  instagram https://www.instagram.com/billieeilish/

PYTHONPATH=backend .venv/bin/python scripts/social_followers.py \
  tiktok https://www.tiktok.com/@billieeilish

# Après configuration serveur de YOUTUBE_API_KEY :
PYTHONPATH=backend .venv/bin/python scripts/social_followers.py \
  youtube https://www.youtube.com/@BillieEilish
```

Le script retourne une observation JSON, y compris les arrondis, ou un statut explicite avec code de sortie non nul. Il ne demande pas de mot de passe de réseau social.

## Limites

Les observations publiques peuvent être arrondies, masquées, périmées chez leur fournisseur ou temporairement inaccessibles. Une URL associée est une association métier explicite, pas une certification de l’identité par Radar. Une exploitation commerciale à grand volume demande de vérifier les conditions des plateformes et de privilégier les accès officiels autorisés. Le suivi historique commence aux collectes réalisées ; aucun historique antérieur n’est inventé.

## Rafraîchissement de la fiche

Le contrôle navigateur a révélé deux défauts préexistants qui empêchaient de présenter les nouvelles observations : le polling attendait `COMPLETED/FAILED` alors que le worker termine en `DONE/PARTIAL/ERROR`, et les observateurs React Query restaient attachés à un ancien client après changement d’identité du cache. Le polling traite les statuts réels ; les observateurs sont remontés au changement d’utilisateur/workspace. Le workspace sélectionné reste stable pendant une recharge de l’abonnement pour éviter une boucle de remontage. Le parcours de sauvegarde des profils et de fin d’enrichissement est vérifié avec des API explicitement simulées dans le navigateur, en complément des tests HTTP réels décrits plus haut.


## Validation livrée

142 tests backend passent. Le typage TypeScript et le build passent. Le navigateur valide sauvegarde, affichage des arrondis et fin d’enrichissement DONE/PARTIAL à 1440 et 390 pixels ; le catalogue et la navigation passent à 1440, 768 et 390 pixels. Ces scénarios navigateur utilisent des fixtures identifiées, alors que les observations Instagram/TikTok du premier tableau sont issues de requêtes publiques réelles. Le débordement et le nom d’artiste masqué sur mobile ont été corrigés. La validation YouTube réelle reste bloquée par la configuration de clé manquante.
