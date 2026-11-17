# Auditeurs mensuels Spotify : collecte gratuite vérifiée

## Solution retenue

Une requête HTTP vers la page publique `https://open.spotify.com/artist/{id}` suffit actuellement. Spotify inclut un script `initialState` contenant du JSON encodé en base64. Le champ utilisé est :

```text
entities.items["spotify:artist:{id}"].stats.monthlyListeners
```

Le collecteur valide la clé et l’URI de l’artiste demandé. Il ne cherche pas un nombre quelconque dans les recommandations, ne confond pas auditeurs et abonnés et ne transforme pas le texte arrondi des métadonnées (par exemple `27.9M`) en valeur prétendument exacte.

Aucune clé API, connexion Spotify, prestation payante ou instance Playwright nécessaire à cette collecte. Le logiciel réutilise HTTPX, BeautifulSoup, Redis et les tâches existantes. L’hébergement et les traitements restent à la charge de l’exploitant. Cette mesure représente les auditeurs sur la fenêtre Spotify de 28 jours, pas les écoutes cumulées ni les abonnés.

Références : [documentation de l’API artiste standard](https://developer.spotify.com/documentation/web-api/reference/get-an-artist) (qui ne déclare pas ce champ), [définition des segments d’audience Spotify](https://support.spotify.com/na-en/artists/article/audience-segments/).

## Vérification réelle du 20 octobre 2026

Tests HTTP sans authentification, avec le nouveau collecteur :

| Artiste et source | Auditeurs publiés récupérés | Collecte UTC |
|---|---:|---|
| [Daft Punk](https://open.spotify.com/artist/4tZwfgrHOc3mvqYlEYSvVi) | 27 902 851 | 08:54:59 |
| [The Weeknd](https://open.spotify.com/artist/1Xyo4u8uXC1ZmMpatF05PJ) | 116 583 387 | 08:54:59 |
| [Stromae](https://open.spotify.com/artist/5j4HeCoUlzhfWtjAfM1acR) | 18 583 546 | 08:55:00 |
| [Thomas Bangalter](https://open.spotify.com/artist/41vv2Tj1knysv6MuFUmdwi) | 243 292 | 09:00:09 |

Ces valeurs sont des observations de test datées, pas des constantes à afficher dans Radar. Elles peuvent changer après la collecte. L’heure de collecte n’est pas une garantie de l’heure de mise à jour des chiffres chez Spotify.

## Intégration dans Radar

- `app/enrichment/providers/spotify_scraper.py` : remplace l’ancien navigateur et son extraction regex fragile ; requête HTTP bornée (taille 2 Mo, délais de connexion/lecture), décodage ciblé et cache 12 heures.
- `discovery_pipeline.step_spotify` : conserve URL, précision et date de collecte dans les snapshots JSON existants. La version de parser change pour ne pas réutiliser les anciens snapshots incomplets comme une preuve de collecte valide. Zéro est accepté s’il est réellement publié.
- `spotify_search_pipeline` et `intelligence/spotify_client.py` : utilisent le collecteur ; aucun remplacement d’un nombre manquant par un multiplicateur des abonnés/popularité dans ces parcours. Les anciens helpers heuristiques non utilisés restent conservés.
- Fiche Discovery : source cliquable et date effective de collecte, y compris lorsque la donnée provient du cache. La date d’enregistrement du snapshot reste disponible séparément.
- Pas de nouvelle migration de schéma : métadonnées stockées dans les JSON existants. Les droits d’abonnement restent contrôlés côté backend.

Les réponses 401/403/404/429, redirections, erreurs réseau, pages trop grandes et changements de structure ne fournissent pas de chiffre. Les échecs HTTP sont mis en cache 15 minutes et un 429 suspend les nouvelles lectures pendant ce délai via Redis. Aucun endpoint privé, récupération de jeton, rotation de proxies ou contournement de blocage.

## Reproduire

Depuis la racine, avec les dépendances backend installées et la configuration Redis habituelle :

```bash
PYTHONPATH=backend .venv/bin/python scripts/spotify_monthly_listeners.py \
  https://open.spotify.com/artist/4tZwfgrHOc3mvqYlEYSvVi
```

La commande renvoie la valeur entière, l’URL source, la date UTC et la précision, ou `status: unavailable` avec un code de sortie non nul. Un identifiant Spotify de 22 caractères est aussi accepté.

## Qualité et limites

La suite automatique couvre notamment : mauvaise identité, données d’un artiste recommandé, champs absents ou invalides, valeur nulle réellement publiée, arrondis SEO, cache et conservation de sa date, blocages HTTP, 429 global, erreurs réseau, limite de taille et absence de substitution des abonnés. La persistance de provenance et sa restitution dans l’API Discovery sont testées sur PostgreSQL.

Le succès sur quatre artistes démontre la faisabilité actuelle ; il ne garantit pas une disponibilité universelle ou durable. Cette structure HTML est une interface publique non contractuelle et peut changer. Prévoir un faible volume, le cache et une surveillance du taux d’échec ; un blocage doit rester un état indisponible. L’adéquation aux conditions d’utilisation de Spotify doit être vérifiée avant exposition commerciale à grande échelle.

L’historique se constitue à partir des observations futures des tâches existantes. Aucun historique antérieur n’est inventé. Cette livraison ne valide pas les collecteurs YouTube, Instagram ou TikTok.
