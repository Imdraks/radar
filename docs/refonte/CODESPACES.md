# Tester Radar dans GitHub Codespaces

Configuration de test sur la branche `refactor/radar-product-security`. Ne pas créer le Codespace depuis une ancienne version de `main` en attendant la fusion de la PR. Aucune installation sur un serveur client n'est nécessaire.

## Premier démarrage

1. Sur GitHub, sélectionner la branche, puis **Code → Codespaces → Create codespace**.
2. Attendre la fin de l'installation et le message **Radar prêt** dans le terminal des tâches du conteneur. Le premier démarrage installe Python, Node 24 et les dépendances, prépare la base jetable et compile la page de connexion.
3. Dans **Ports**, ouvrir **3000** dans le navigateur. Le port reste privé ; être connecté au compte GitHub autorisé pour ce Codespace.
4. Afficher les identifiants générés avec `python .devcontainer/radar.py credentials`, puis se connecter dans Radar. Le mot de passe est conservé dans un fichier local ignoré de Git, pas dans le dépôt ou les logs de démarrage.

La préversion crée un compte d'agence Business, sans privilège de plateforme. Aucun chiffre artistique, facture, encaissement ou contrat accepté n'est prérempli comme donnée réelle.

## Services démarrés et vérification

Le lancement prépare PostgreSQL et Redis via Compose puis démarre l'API, le worker consommant les quatre files, Celery Beat et Next.js. Il attend les services avant d'annoncer le succès. Les processus restent protégés par leur identité de démarrage pour ne pas arrêter un PID réutilisé par un autre programme.

```sh
python .devcontainer/radar.py check
python .devcontainer/radar.py restart
python .devcontainer/radar.py stop
```

`check` vérifie le marqueur et les colonnes de la base de test, Redis, les processus, la connexion réelle au compte via le proxy du frontend et une tâche réellement traitée sur chacune des quatre files Celery. L'état du planificateur indique un processus actif ; ce n'est pas la preuve qu'une collecte externe a abouti. Le diagnostic signale séparément les configurations fournisseur absentes, sans afficher leurs valeurs ni inventer un succès.

Après modification du code, récupérer la branche puis exécuter `restart`. Après changement de version Node ou de configuration du conteneur, utiliser **Codespaces: Rebuild Container**. Conserver les données locales et le volume PostgreSQL ; ne pas les effacer pour contourner une erreur.

## Activer les intégrations réelles avec des secrets de test

Les secrets génériques de production sont retirés de l'environnement de préversion. Pour utiliser tes propres intégrations, ajouter les valeurs dans **GitHub → Settings → Codespaces → Secrets**, autoriser le dépôt `Imdraks/radar`, puis redémarrer le Codespace pour qu'il les reçoive. Ce sont les secrets **Codespaces**, pas uniquement les secrets Actions.

| Service | Secrets / variables de test à fournir |
|---|---|
| Spotify API | `RADAR_TEST_SPOTIFY_CLIENT_ID`, `RADAR_TEST_SPOTIFY_CLIENT_SECRET` |
| YouTube Data API | `RADAR_TEST_YOUTUBE_API_KEY` |
| Google Drive, Calendar et SSO | `RADAR_TEST_GOOGLE_CLIENT_ID`, `RADAR_TEST_GOOGLE_CLIENT_SECRET`, puis autorisation dans Radar |
| OpenAI | `RADAR_TEST_OPENAI_API_KEY`, éventuellement `RADAR_TEST_OPENAI_MODEL` |
| Groq | `RADAR_TEST_GROQ_API_KEY` |
| Recherche Tavily | `RADAR_TEST_TAVILY_API_KEY` |
| Concerts Ticketmaster | `RADAR_TEST_TICKETMASTER_API_KEY` |
| Formulaire de contact | PostgreSQL et migration 064 ; aucun e-mail à la soumission. |
| Accusé à la première ouverture du dossier | Resend ou SMTP configuré pour les tests, worker actif et destinataire de test autorisé. |
| SMTP | `RADAR_TEST_SMTP_HOST`, `RADAR_TEST_SMTP_PORT`, `RADAR_TEST_SMTP_USER`, `RADAR_TEST_SMTP_PASSWORD`, `RADAR_TEST_SMTP_FROM_EMAIL`, si besoin `RADAR_TEST_SMTP_USE_TLS` |
| IMAP | `RADAR_TEST_IMAP_HOST`, `RADAR_TEST_IMAP_PORT`, `RADAR_TEST_IMAP_USER`, `RADAR_TEST_IMAP_PASSWORD`, éventuellement `RADAR_TEST_IMAP_FOLDER` et `RADAR_TEST_IMAP_USE_SSL` |
| Collecte Viberate | `RADAR_TEST_VIBERATE_ENABLED=true`, si besoin `RADAR_TEST_VIBERATE_REQUEST_DELAY` |

Les préfixes sont convertis uniquement pour les champs explicitement autorisés. Les secrets API, mots de passe applicatifs et accès à la base ne sont pas transmis au processus Next.js. Aucune valeur ne doit être committée ou collée dans une conversation. Le lanceur ne charge pas le fichier `.env` du dépôt.

Les invitations email restent désactivées par défaut ; `RADAR_TEST_SEND_INVITATION_EMAILS=true` permet de les tester une fois le fournisseur configuré. Les tâches planifiées sont actives et peuvent utiliser les intégrations que tu configures : utiliser des comptes et destinataires de test, et tenir compte des quotas ou coûts réels des fournisseurs. Le diagnostic ne leur envoie pas de message de test automatiquement.

Une clé présente n'est pas une preuve d'accès fournisseur : les autorisations, quotas, connexions et parcours réels doivent être testés. Les auditeurs mensuels Spotify publics sont distincts des abonnés fournis par l'API ; une API ne donne pas automatiquement toutes les métriques Instagram/TikTok. Le logiciel doit conserver leurs sources et données manquantes.

## Google : URL de retour

L'origine de retour est celle du **port 3000**, par exemple `https://NOM-DU-CODESPACE-3000.app.github.dev`, et non localhost:8000. Ajouter dans la configuration OAuth Google les URI réellement utilisées :

- `https://NOM-DU-CODESPACE-3000.app.github.dev/api/v1/drive/auth/callback`
- `https://NOM-DU-CODESPACE-3000.app.github.dev/api/v1/calendar/google/callback`
- Pour le SSO : `https://NOM-DU-CODESPACE-3000.app.github.dev/api/v1/auth/sso/google/callback`

Utiliser le domaine de redirection affiché par ton Codespace si différent, activer les API Google nécessaires et autoriser le compte Google dans l'application de test du fournisseur. Avec le compte Radar de test, connecter Drive/Calendar depuis les intégrations ; le SSO avec un autre email doit respecter les invitations et autorisations Radar. Les protections ne sont pas désactivées pour contourner un refus.

## Anciennes préversions et schéma

Le lanceur ne peut cibler que la base interne `radar_codespaces_test`. Il initialise uniquement une base vide ou reconnaît le marqueur exact de sa propre instance. Il refuse toute base non reconnue. Sur une ancienne préversion reconnue, il ajoute les tables manquantes et une liste limitée de colonnes nullables connues (preuves et mentions de facture, avoirs, acceptations), avec une valeur conservatrice pour la confidentialité des commentaires. Comptes, mots de passe, noms modifiés et données présentes sont conservés. Toute autre divergence de schéma bloque le démarrage au lieu d'annoncer un faux succès.

Ce schéma jetable reste construit depuis les modèles, sans marquage Alembic fictif. Le graphe de migrations de production a été réparé et testé séparément ; cette réparation de préversion ne constitue pas une migration d'une base client. Aucun downgrade destructeur ni réinitialisation automatique n'est utilisé.

## Si une erreur apparaît

- **401 avant la page Radar** : vérifier la connexion GitHub et l'accès au port privé 3000 depuis l'onglet Ports. Ce contrôle GitHub est distinct du formulaire de connexion Radar.
- **401 dans le formulaire Radar** : utiliser les identifiants de cette instance ; ne pas réutiliser le mot de passe généré dans un autre Codespace.
- **502** : attendre le démarrage, exécuter `check`, consulter le journal du service en échec puis relancer `restart`. Ne pas démarrer plusieurs Next.js sur le même port.
- **Erreur fournisseur / fonctionnalité externe indisponible** : consulter les variables manquantes du diagnostic, les autorisations et quotas ; aucune donnée de remplacement n'est présentée comme un résultat réel.

Journaux locaux : `.devcontainer/.local/backend.log`, `worker.log`, `beat.log`, `frontend.log`. Les données et identifiants de cette préversion sont jetables. Arrêter le Codespace depuis GitHub pour arrêter le calcul ; `stop` arrête les processus Radar, pas la facturation de l'hébergement GitHub. La gratuité dépend du quota disponible sur ton compte.

Les modules bancaires reportés, la transmission via plateforme agréée non connectée et la publication commerciale soumise aux conditions juridiques ne sont pas activés artificiellement dans cette préversion.
