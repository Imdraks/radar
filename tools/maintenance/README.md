# Maintenance explicite

Ces outils sont destinés à un opérateur ayant déjà accès à la base. Ce ne sont
pas des API utilisateur et ils ne remplacent pas les permissions de Radar.
Aucun outil ne doit ouvrir une connexion ou modifier des données à l’import.

## Inventaire des clients, en lecture seule

Depuis la racine du dépôt, avec les dépendances backend et la configuration de
la base destinataire :

```bash
PYTHONPATH=backend python tools/maintenance/list_clients.py --workspace-id 123 --kind both --limit 50
```

Sur le VPS existant, pour utiliser la configuration du conteneur backend :

```bash
sudo -v
sudo docker exec -i radar-backend-1 python - --workspace-id 123 --kind both --limit 50 < /opt/radar/tools/maintenance/list_clients.py
```

Remplacer `123` par l’identifiant explicite du workspace. Le script n’affiche
que les identifiants et noms, avec un plafond de 500 lignes par catégorie.
La transaction PostgreSQL est déclarée READ ONLY. Ne pas partager la sortie
sans vérifier les informations client qu’elle contient.

## Anciens scripts

Les anciens fichiers check_clients.py, list_clients.py, list_billing_clients.py,
create_test_client.py, delete_client.py, delete_billing_client.py et sync_client.py
sont conservés dans la branche `archive/pre-cleanup-20261119`.

Les quatre derniers contenaient des mutations au niveau du module, avec des
identifiants ou données de démonstration codés en dur. Ils sont retirés du chemin
actif plutôt que déplacés tels quels et présentés comme sûrs. Les créations,
modifications, suppressions et synchronisations passent par les interfaces/API
existantes avec leurs contrôles d’accès. Aucune de ces opérations n’a été exécutée
pendant le nettoyage.
