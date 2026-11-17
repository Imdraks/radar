# Outils artistes du connecteur MCP Radar

Ce correctif vise le connecteur installé sur le VPS dans
`/opt/radar/chatgpt-connector`, à partir des trois fichiers transmis par son
propriétaire le 16 novembre 2026. Ce serveur MCP n'était présent sur aucune des
deux branches GitHub inspectées. Le correctif est livré séparément pour éviter
d'écraser son OAuth, son stockage, son catalogue complet et ses configurations.

## Comportement

| Outil | Accès | Résultat |
| --- | --- | --- |
| `search_artists` | `radar:read` | Recherche locale et catalogue Deezer par nom ; résolution d'URL Spotify/Viberate. Aucun travail d'enrichissement déclenché. |
| `get_artist_profile` | `radar:read` | Fiche par UUID, ou suivi par `job_id`. Les erreurs techniques brutes des travaux ne sont pas retournées. |
| `save_artist` | `radar:read radar:write` | Réutilise `/artists/search` puis `/artists/analyze`. Un artiste déjà enregistré n'est pas réenrichi ; un résultat ambigu exige une sélection. |
| `compare_artists` | `radar:read` | Compare 2–5 UUID distincts sans modifier de liste, après validation du droit `comparison` par le backend. |

L'enregistrement reste asynchrone. `JOB_CREATED` et `ALREADY_RUNNING` ne prouvent
pas que l'artiste est enregistré ni que des statistiques ont été obtenues.
`get_artist_profile(job_id=...)` rapporte l'état réel et lit le profil lorsque le
travail est `DONE` ou `PARTIAL`. Les sources, dates, limites et données manquantes
du profil Discovery sont conservées. Aucun auditeur mensuel Spotify n'est déduit
du nombre de fans Deezer. Sans métriques calculées, le score absent est `null`.

Les quatre noms remplacent leurs éventuelles définitions générées du catalogue,
sans doublons. Ils apparaissent aussi dans `search_radar_tools` et les comptes de
`get_radar_capabilities`. Les outils CRM et les autres outils générés sont conservés.
Le contrôle de consentement OAuth existant et `bridge.checkAccess` sont inchangés.
Le workspace vient exclusivement du grant existant, jamais d'un argument d'outil.
Les API Radar conservent leurs contrôles de permissions et d'abonnement.

## Installation sur le VPS

L'archive contient uniquement ce correctif et ses tests, aucun secret. Depuis
l'ordinateur qui a téléchargé `radar-mcp-artistes.tar.gz` :

```bash
scp radar-mcp-artistes.tar.gz ubuntu@51.255.166.15:/tmp/
```

Sur le VPS, connecté en `ubuntu` :

```bash
mkdir -p "$HOME/radar-mcp-artistes"
tar -xzf /tmp/radar-mcp-artistes.tar.gz -C "$HOME/radar-mcp-artistes"
sudo python3 "$HOME/radar-mcp-artistes/install.py" /opt/radar/chatgpt-connector --node-image radar-chatgpt:local
```

Cette première commande d'installation vérifie les ancres du code existant et la
syntaxe JavaScript, sans modifier le connecteur. Une version différente ou un
module artiste préexistant provoque un refus explicite. Le contrôle utilise Node dans l’image Docker locale `radar-chatgpt:local`,
sans démarrer sa commande de service, charger ses secrets ou monter ses volumes.
Il ne nécessite pas Node sur le VPS et ne télécharge aucune image. Si ce contrôle réussit, arrêter uniquement le MCP :

```bash
cd /opt/radar
sudo docker compose -f compose.server.yml -f compose.mcp.yml stop mcp
sudo python3 "$HOME/radar-mcp-artistes/install.py" /opt/radar/chatgpt-connector --node-image radar-chatgpt:local --apply
sudo docker compose -f compose.server.yml -f compose.mcp.yml up -d --build --no-deps mcp
sudo docker compose -f compose.server.yml -f compose.mcp.yml ps mcp
```

Ces noms de fichiers et le service `mcp` correspondent aux labels Docker fournis
par le propriétaire. Aucun autre service n'est redémarré. Ne pas utiliser `down -v`.
Si l'installation ou le build échoue, ne pas poursuivre à l'aveugle : restaurer
la sauvegarde puis démarrer le MCP sans `--build` pour utiliser l'image précédente.

Le script sauvegarde `catalog-tools.mjs` et `tools.mjs` dans
`/opt/radar/chatgpt-connector/.artist-patch-backups/<date>/`, ajoute
`src/artist-tools.mjs`, adapte la découverte et les instructions, et préserve les
autres fichiers, leurs propriétaires et leurs permissions. Ne pas régénérer ou
copier de `.env`, de store OAuth ou de mot de passe pour installer ce correctif.

## Retour arrière

Remplacer `<date>` par le dossier annoncé pendant l'installation :

```bash
cd /opt/radar
sudo docker compose -f compose.server.yml -f compose.mcp.yml stop mcp
sudo python3 "$HOME/radar-mcp-artistes/install.py" /opt/radar/chatgpt-connector \
  --rollback /opt/radar/chatgpt-connector/.artist-patch-backups/<date>
sudo docker compose -f compose.server.yml -f compose.mcp.yml up -d --build --no-deps mcp
```

Après un build échoué, utiliser `up -d --no-deps mcp` sans `--build` pour
redémarrer l'image précédente, puis diagnostiquer le build avant une nouvelle tentative.

## Vérification dans ChatGPT

Actualiser la connexion Radar pour recharger sa liste d'outils. Si nécessaire,
déconnecter puis reconnecter le connecteur ; cela peut créer un nouveau grant.

1. Demander `get_radar_capabilities`, puis `search_radar_tools` avec « artists ».
   Vérifier les quatre noms et l'absence de doublons.
2. Demander « Recherche SCH dans Radar et dans le catalogue public ». Une panne
   Deezer doit être annoncée, sans chiffres inventés.
3. Demander explicitement un enregistrement. Avec `radar:read` seul, un consentement
   `radar:write` doit être demandé avant tout appel d'écriture au backend.
4. Suivre le `job_id` avec `get_artist_profile`. Vérifier la réponse du worker,
   les sources disponibles et les données manquantes avant de conclure.
5. Comparer deux UUID enregistrés dans le même workspace. Un UUID inexistant ou
   appartenant à un autre workspace doit être refusé sans exposer son profil.

## Tests et limites

Tests reproductibles du correctif : Node 24, Python 3, Zod 4.6.7.

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

Résultats locaux : 17 tests d'outils et 7 tests de l'installateur (dont le contrôle Docker sans Node sur l'hôte).
Quatre tests supplémentaires ont utilisé les fichiers complets fournis et un SDK
MCP 1.26.0 avec transports mémoire : découverte sans doublons, métadonnées OAuth,
refus d'écriture sans scope, travail en attente et refus tenant. Le catalogue de
ces tests d'intégration était une fixture explicite : le vrai `catalog.json` et
la version du SDK installée sur le VPS n'ont pas été fournis. Application,
réapplication et retour arrière ont aussi été vérifiés sur une copie des fichiers.

Ces tests ne constituent pas une validation sur le VPS : aucun déploiement SSH,
appel aux fournisseurs réels, travail Celery réel ni parcours ChatGPT distant
n'a pu être exécuté depuis cet environnement. Les tests de refus tenant contrôlent
la propagation d'un refus backend simulé, pas une base multi-workspace réelle.

La résolution d'URL et l'enrichissement réutilisent les routes POST existantes ;
leur politique backend peut refuser un membre en lecture seule. Les collectes
Spotify/YouTube/Instagram/TikTok restent dépendantes de la configuration, des
quotas et des droits fournisseurs. Les fans Deezer ne remplacent pas ces données.
Un problème de dispatch Celery reste un problème backend : ce correctif ne répare
pas les éventuels travaux laissés en file lors d'une panne du broker.

L'installateur doit être exécuté service MCP arrêté ; une installation n'est pas
une opération atomique sur plusieurs fichiers pour un processus qui continue de
les lire. Aucune migration de base de données n'est nécessaire.
