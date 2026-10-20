# Tester Radar dans GitHub Codespaces

Cette configuration lance la branche de refonte dans un environnement privé et jetable. Elle n’accède pas à la production. GitHub applique les quotas et la facturation de ton compte : vérifier le quota disponible et le budget Codespaces avant de créer une machine. Ce n’est pas un hébergement permanent gratuit.

## Ouvrir et se connecter

1. Ouvrir [la création du Codespace Radar](https://codespaces.new/Imdraks/radar?ref=refactor%2Fradar-product-security).
2. Vérifier la branche `refactor/radar-product-security` et choisir la configuration **Radar — test privé**. Utiliser une machine de 2 cœurs pour commencer ; le premier démarrage installe les dépendances et peut prendre plusieurs minutes.
3. Attendre la fin de l’installation et le message `Radar prêt`. Si le navigateur ne s’ouvre pas, aller dans l’onglet **Ports**, puis ouvrir le port **3000**. Garder sa visibilité **Private**.
4. Dans le terminal du Codespace, exécuter `python .devcontainer/radar.py credentials`. Utiliser l’email et le mot de passe affichés pour se connecter à Radar.

Le compte est un administrateur d’agence, sans accès administrateur plateforme. Son workspace **TEST — Codespaces (données jetables)** dispose du plan Business uniquement dans cette base de test. Les mots de passe et clés JWT sont aléatoires, propres au Codespace, conservés dans un fichier local ignoré par Git avec des droits `0600`. Aucun identifiant fixe n’est publié.

## Parcours à essayer

- Créer un projet, une tâche et un événement ; vérifier leur affichage après rechargement.
- Rechercher un artiste par URL Spotify, ouvrir sa fiche et lancer son enrichissement. Vérifier les sources et dates des observations.
- Ajouter les URL publiques Instagram, TikTok et YouTube à la fiche, enregistrer, puis relancer l’enrichissement. Un compteur indisponible reste signalé comme manquant.
- Créer un client et un devis brouillon. Les paiements réels, les emails et les intégrations personnelles ne sont pas configurés.

Spotify, Instagram et TikTok dépendent de l’accès autorisé aux pages publiques par leurs fournisseurs. Le compte TikTok peut être inaccessible ou son compteur indisponible ; aucune valeur n’est inventée. Pour YouTube, ajouter éventuellement le secret Codespaces `YOUTUBE_API_KEY`, l’autoriser pour ce dépôt puis redémarrer le Codespace. Cette clé optionnelle reste côté serveur. Les autres clés de production ne doivent pas être ajoutées à cette préversion.

## Démarrage et arrêt

Le frontend Next.js utilise le port 3000 et transmet les API à FastAPI sur le port interne 8000. PostgreSQL et Redis ne publient aucun port sur l’hôte. Un worker Celery traite les enrichissements demandés. Aucun ordonnanceur Celery Beat n’est lancé : les collectes récurrentes et les synchronisations planifiées ne sont pas validées par ce montage.

Les services démarrent automatiquement à la reprise du Codespace. Pour relancer manuellement :

```sh
python .devcontainer/radar.py stop
python .devcontainer/radar.py start
```

Les journaux se trouvent dans `.devcontainer/.local/backend.log`, `worker.log` et `frontend.log`. Ne pas partager le fichier `account.json` ni des journaux contenant des données personnelles.

Arrêter **le Codespace entier** depuis le menu GitHub Codespaces après les tests pour arrêter le calcul. La commande `stop` ci-dessus arrête seulement les processus Radar. Le stockage du Codespace peut continuer à compter dans ton quota tant qu’il existe. Supprimer le Codespace lorsqu’il n’est plus utile ; les données de test ne sont pas destinées à être conservées.

## Base de test et limites de validation

Le script ne peut cibler que le service PostgreSQL interne `postgres`, la base `radar_codespaces_test` et le compte `radar_test`. Il initialise uniquement une base vide et inscrit un marqueur d’instance. Une base non vide sans marqueur ou appartenant à une autre instance est refusée. Les redémarrages ne recréent pas les utilisateurs et ne modifient pas leurs données.

Le schéma jetable est créé depuis les modèles SQLAlchemy, comme pour les tests locaux précédents. Le [blocage historique Alembic](MIGRATIONS.md) reste intact : aucun marquage de migration ni réécriture de l’historique n’est effectué. Cette préversion ne valide donc pas l’installation ou la mise à jour d’une base de production. Un changement ultérieur des modèles peut nécessiter un nouveau Codespace vide ; le lanceur ne migre pas automatiquement une base de test existante.

Les protections applicatives et les droits backend restent actifs. L’environnement est identifié par son nom de workspace ; aucune statistique artistique ou transaction commerciale n’est préremplie.

Validation avant publication de la configuration : JSON, syntaxe Python 3.11, syntaxe shell et `docker compose config` passent. La suite backend compte **147 tests réussis**, dont cinq couvrant les identifiants privés, l’isolation de configuration, le refus des bases non reconnues, la conservation au redémarrage et la connexion réelle au compte d’agence. Le contrôle des PID réutilisés est également vérifié. Le lancement complet d’un Codespace sur GitHub reste à effectuer depuis ton compte ; ces contrôles ne sont pas présentés comme une session Codespaces déjà ouverte.
