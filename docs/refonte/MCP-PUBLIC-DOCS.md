# Présentation MCP et documentation publique

## Livrable

- `/mcp` : page de présentation du connecteur ChatGPT / MCP, extension payante
  Radar Addons avec conditions sur demande, exemples explicitement illustratifs,
  périmètre, permissions, limites, FAQ et accès à la documentation en bas de page.
- `/doc` : index public avec navigation responsive et recherche dans le contenu
  des guides, insensible aux accents et à la casse.
- `/doc/<sujet>` : 20 guides statiques, avec sommaire, étapes, liens utiles,
  métadonnées et date de révision. Les sujets inexistants affichent une page 404.
- Liens dans le header et le footer publics et dans la barre de l'application.
- Le contact depuis `/mcp` préremplit une demande Radar Addons / MCP sans l'envoyer.
- Sitemap enrichi avec les pages et tous les guides.

Le contenu est centralisé dans `frontend/src/content/documentation.ts`. Il décrit
les parcours et les restrictions connus du dépôt et des fichiers MCP fournis. Il
ne garantit pas la connexion des fournisseurs de chaque workspace. Aucun prix,
témoignage, chiffre d'audience ou confirmation de paiement n'est inventé. Les
limitations des exports, avoirs complets, réseaux sociaux et transmissions
réglementaires de factures électroniques restent explicites.

Le formulaire existant transmet la demande ; il ne vend pas ni n'active
automatiquement le connecteur. Cette présentation ne crée aucun droit payant
backend. Le serveur MCP installé sur le VPS conserve son contrôle OAuth et les
droits métiers Radar. L'attribution et la révocation commerciales spécifiques du
MCP devront être validées côté serveur avant une vente automatisée. Le verrou de
publication commerciale existant n'est pas modifié.

## Attention : `/mcp` est aussi le transport existant

Le 16 novembre 2026, le contrôle public a constaté :

- `GET /mcp` avec `Accept: text/html` : 401 JSON avec challenge OAuth ;
- `GET /doc` : 404 ;
- bloc Nginx fourni par le propriétaire : `location = /mcp` vers `127.0.0.1:13100`.

Créer une page Next.js seule ne suffit donc pas à publier `/mcp`. Ne pas changer
son URL de transport, ses métadonnées OAuth ou les routes `/authorize`, `/token`,
`/register` et `/.well-known/oauth-*`. Ne pas faire rediriger tous les appels MCP
vers la page HTML.

Les deux snippets dans `docker/nginx/snippets/` proposent un dispatch :

| Méthode et Accept | Destination |
| --- | --- |
| GET/HEAD contenant `text/html` | Frontend, page `/mcp` |
| POST, même avec `text/html` | MCP existant |
| GET JSON, SSE ou sans Accept HTML | MCP existant |
| Autres méthodes | MCP existant |

La page HTML force un rendu dynamique avec une réponse non stockable par Next ;
les caches proxy sont désactivés sur ces blocs. Aucun `add_header` local ne vient
remplacer et supprimer les protections héritées du serveur Nginx.

## Déploiement sur le VPS

Le `/opt/radar` du propriétaire est une copie de fichiers, pas un checkout Git.
Ne pas y exécuter `git pull` et ne pas remplacer ses fichiers Compose, `.env`,
stockages OAuth ou configurations locales par ceux du dépôt.

Le paquet de déploiement préparé contient un `frontend.patch` limité aux sources
publiques, les deux snippets et `deploy.py` (source :
`scripts/deploy_public_pages.py`). Il vérifie le patch sans approximation, le
contexte Docker et l'unicité du bloc Nginx d'origine dans les fichiers actifs.
Sans `--apply`, aucun fichier ni service n'est modifié. Avec `--apply`, il
sauvegarde les fichiers concernés, construit le frontend pendant que l'ancien
sert encore, vérifie `/doc` et `/mcp` sur le port 13000, puis valide et recharge
Nginx. En cas d'échec, il tente de restaurer les fichiers et l'image précédente.
Il refuse une version locale incompatible au lieu de l'écraser. Ses sept tests
incluent le retour arrière après échec de build et de validation Nginx.

1. Sauvegarder les fichiers frontend et la configuration Nginx active.
2. Le propriétaire a confirmé le mapping frontend :
   `3000/tcp -> 127.0.0.1:13000`. Le snippet utilise donc cet upstream.
3. Déployer les sources frontend du commit retenu en préservant les variables,
   les personnalisations locales et les secrets. La création d'une copie de
   build isolée est préférable à un écrasement du répertoire actuel.
4. Reconstruire uniquement le frontend avec les fichiers réellement utilisés :
   `sudo docker compose -f compose.server.yml up -d --build --no-deps frontend`.
   Cette commande suppose que son contexte de build a reçu les sources mises à
   jour ; elle ne les télécharge pas à elle seule.
5. Vérifier `/doc` et `/mcp` directement sur le frontend avant d'adapter Nginx.
6. Charger le map dans le contexte `http`. Remplacer uniquement le bloc exact
   `/mcp` par le snippet location et son bloc nommé. Ajuster l'upstream du
   frontend au port confirmé : `127.0.0.1:13000`.
7. Exécuter `sudo nginx -t`, puis `sudo systemctl reload nginx` seulement si le
   contrôle réussit. Ne pas redémarrer le MCP ni changer les routes OAuth.

Contrôles publics après déploiement :

```bash
curl -sS -o /dev/null -w '%{http_code} %{content_type}\n' \
  -H 'Accept: text/html' https://radarapp.fr/mcp
curl -sS -o /dev/null -w '%{http_code} %{content_type}\n' \
  https://radarapp.fr/doc
curl -sS -o /dev/null -w '%{http_code} %{content_type}\n' \
  -H 'Accept: application/json, text/event-stream' https://radarapp.fr/mcp
```

Résultats attendus : 200 HTML, 200 HTML, puis refus d'authentification MCP
sans token (généralement 401), jamais une page HTML pour le dernier appel.
Effectuer ensuite un appel authentifié `get_workspace` dans ChatGPT et ouvrir
plusieurs guides sur mobile. Une page 200 ne prouve pas le fonctionnement des
intégrations externes.

En cas d'échec, restaurer les fichiers Nginx sauvegardés, valider par `nginx -t`
puis recharger. Revenir à l'image frontend précédente selon la procédure de
déploiement. Aucun changement de schéma ni migration de données n'est nécessaire.

## Validation locale

- `npm run type-check` et `npm run build` dans `frontend`.
- `scripts/documentation_ui_smoke.py` : pages, recherche, liens, métadonnées,
  contact prérempli et contrôles responsive. Les réponses API des tests navigateur
  sont des fixtures explicites, jamais des données d'utilisateurs.
- Ajouter ce smoke à la CI existante ; les parcours publics précédents restent
  vérifiés par `scripts/brand_ui_smoke.py`.
- `scripts/check_mcp_public_proxy.py` vérifie les snippets avec Nginx 1.28 dans
  un conteneur sans réseau ni port publié, avec des upstreams de test explicites.
  Huit variantes de méthode/Accept et la conservation d'une route de métadonnées
  OAuth passent. Ce test est également ajouté au job CI du correctif MCP.

Résultats locaux : typage et build de production réussis ; 20 guides et sitemap
vérifiés ; parcours MCP/documentation/contact à 1440, 1024, 768 et 390 pixels ;
régression des 15 pages publiques existantes à trois tailles d'écran ; aucun
débordement horizontal ni erreur JavaScript observé. La réponse HTML `/mcp`
contient `Cache-Control: private, no-cache, no-store, max-age=0, must-revalidate`.

La configuration Nginx de production ne peut être considérée comme installée
avant intervention sur le VPS et vérification de l'accès MCP authentifié.
