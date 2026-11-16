# Déployer A2F et sessions sur le VPS existant

Le VPS du propriétaire est en révision `056_full_credit_notes`, avec les sources
sous `/opt/radar`, sans dépôt Git. Les fichiers Compose effectifs sont
`compose.server.yml` et `compose.mcp.yml`, projet `radar`. Les contextes Docker
backend/frontend/connecteur et les ports locaux ont été confirmés par le propriétaire.

Le script livre uniquement le correctif A2F et sessions de `67e1efa`, comparé à
`fea31f4`. Il ne copie pas une nouvelle application complète. Les changements
locaux hors des contextes du patch sont préservés ; les conflits provoquent un
arrêt avant toute modification. La variante `auth.py` transmise par le propriétaire
(ajout de `Body` et de `RefreshTokenRequest` pour accepter le JSON) est reconnue
uniquement si le fichier complet correspond exactement à cette variante revue.
Elle migre vers le renouvellement JSON avec contrôle des sessions du nouveau backend ;
aucune autre modification du rafraîchissement n’est adoptée automatiquement. Les pages publiques MCP/doc, les variables d’environnement,
Nginx, Compose et les fichiers métier non concernés ne sont pas remplacés.

Placer `install.py` et `paths.json` du **même commit** dans un répertoire temporaire :

```sh
sudo python3 install.py          # Vérification et préparation temporaire uniquement
sudo python3 install.py --apply  # Sauvegarde, construction, migration, redémarrage
```

Les archives GitHub sont épinglées à deux commits complets, téléchargées en HTTPS ;
seuls les fichiers réguliers attendus sont lus, sans extraction arbitraire.
Le correctif du login MCP existant est reconnu par son empreinte et vérifié avec
Node dans l’image Docker déjà installée. Aucun Node système n’est nécessaire.

En mode application :

1. Vérifier les contextes Docker, les images partagées worker/scheduler, la
   révision 056, l’application du patch et la compatibilité MCP.
2. Sauvegarder les sources concernées et les identifiants des anciennes images
   dans `/opt/radar-deployment-backups/<date>` (répertoire réservé à root).
3. Construire les trois images dans des copies temporaires des contextes actuels.
   Le site existant reste servi pendant cette phase. Les images originales sont
   conservées avec des tags datés. Les fichiers de configuration sont réutilisés.
4. Vérifier la présence de la migration 058, arrêter backend/worker/scheduler/MCP/frontend,
   vérifier que les sources n’ont pas changé, sauvegarder PostgreSQL avec `pg_dump -Fc`
   et vérifier que l’archive peut être lue avec `pg_restore --list`.
5. Installer les seuls fichiers concernés en conservant les propriétaires et
   permissions des fichiers existants, puis appliquer `alembic upgrade head` avec
   la nouvelle image backend. Ni `stamp`, ni suppression de table, ni restauration
   automatique de base n’est utilisée.
6. Redémarrer les cinq services, vérifier `/health` côté backend et `/login` côté
   frontend, afficher la révision et l’état Compose.

Un échec avant la tentative de migration rétablit les sources effectivement
écrites et les tags des anciennes images, puis redémarre les anciens services si
nécessaire. Un échec pendant/après la tentative de migration laisse les nouvelles
sources et images en place : revenir à un ancien backend pourrait contourner les
révocations. Examiner l’erreur et les sauvegardes ; ne pas restaurer automatiquement
l’ancienne base ou un ancien backend.

Les utilisateurs et connecteurs devront se reconnecter une fois. Les facteurs
déjà actifs sont préservés. L’application TOTP fonctionne sans prestataire ;
l’envoi réel d’e-mails et de SMS dépend des fournisseurs configurés. Aucun
fournisseur SMS n’est activé par cet installateur. La rotation des clés existantes
n’est pas effectuée : elles servent notamment à déchiffrer les facteurs existants.

Tests : `python3 -m unittest discover -s integrations/deploy-mfa -p 'test_*.py' -v`.
Les tests Docker/orchestration sont simulés ; ils ne prétendent pas qu’un VPS ou
un fournisseur réel a été contacté. Le patch complet épinglé est réellement
appliqué dans un répertoire temporaire dépourvu de `.git`.
