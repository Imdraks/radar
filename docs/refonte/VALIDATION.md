# Validation du lot de refonte

Vérifications locales du 19 octobre 2026. Aucun accès à la production.

| Vérification | Résultat | Portée et limite |
| --- | --- | --- |
| `pytest backend/tests -q` | **43 tests passent** | PostgreSQL jetable, schéma indépendant par session ; vraies signatures JWT et vrai login, permissions, isolation, droits payants, expiration, demandes/décisions, projets/enfants, devis→facture→paiement, événements, données manquantes, pannes simulées et migrations nouvelles |
| `python -m compileall -q backend/app backend/alembic` | Réussi | Import/syntaxe, pas une preuve fonctionnelle |
| `pip check` | Réussi | Dépendances installées compatibles |
| `alembic heads` | Une tête : `049_billing_numbering` | Ne démontre pas que toute la chaîne historique est applicable |
| `alembic upgrade head`, base entièrement neuve | **Échec préexistant avant 046** | 032 ajoute une colonne déjà créée en 020 ; ordre de création de la branche facturation également à réparer. Historique non modifié après rejet automatique |
| `npm ci` | Réussi | Lockfile régénéré et réinstallation propre ; même méthode retenue dans Docker |
| `npm run type-check` | Réussi | Compilation TypeScript stricte |
| `npm run build` | Réussi | Next.js 15.5.28 ; génération des pages et contrôle de types/lint |
| Chromium, 1440×1000, 768×1024, 390×844 | Réussi | Catalogue partagé, ouverture/fermeture du menu, absence de débordement horizontal et erreur événementielle explicite ; API **simulées et identifiées comme test local** |
| `pip-audit` sur l’environnement actualisé | Aucune vulnérabilité connue signalée | Résultat au jour de la vérification, pas une garantie permanente |
| `npm audit --omit=dev` | 0 critique, **5 élevées et 2 modérées restantes** | Chaîne Tailwind/Chokidar/Micromatch/Braces et parsing CSS. Ne pas présenter le dépôt comme exempt de vulnérabilités |

Les tests backend produisent encore des avertissements de dépréciation : Pydantic Config, événements de démarrage FastAPI, datetime UTC naïves, API TestClient et passlib. Ils ne sont pas comptés comme des échecs ; leur modernisation reste une dette technique.

## Évolution des dépendances

- Next.js 14.1.0 → 15.5.28 ; adaptation ES2017 et maintien de React 18. MapLibre 5 → 6.15 avec adaptation de l’import. Axios → 1.20. Ces mises à niveau répondent aux avis de sécurité observés, sans changer l’architecture Next.js/TypeScript.
- PostCSS 8.5.31 imposé dans Next via override compatible de la même branche majeure, vérifié après installation propre et build.
- FastAPI 0.149, Starlette 1.9, Pydantic 2.14 et bibliothèques HTTP/auth/parsing concernées actualisées. Python 3.11 reste le runtime Docker/CI ; tests locaux exécutés sous Python 3.12.
- PyJWT, déjà présent pour SSO/Revolut, remplace python-jose pour les tokens Radar. Vérification explicite du format HS256 existant, de l’expiration et du type access/refresh ; retrait de la dépendance ECDSA non utilisée.
- Versions d’outillage test et pip actualisées. Le nombre d’alertes Python initial incluait aussi l’outillage de l’environnement ; ce n’est pas un nombre de failles toutes exploitables dans Radar.
- Braces 3.0.3 reste signalé, sans version 3 corrigée publiée au moment de l’audit. Le passage à Tailwind 4 n’a pas été imposé pour masquer ce résultat : il nécessite une migration CSS propre et sa recette. Les alertes restantes sont consignées, pas ignorées dans le rapport.

## Rejouer les tests

Créer un environnement Python à partir de `backend/requirements.txt`. Fournir **uniquement l’URL d’une base PostgreSQL jetable** dans `RADAR_TEST_DATABASE_URL`. Le fixture crée et retire ses propres schémas de test ; ne jamais utiliser une base de production.

```sh
PYTHONPATH=backend TESTING=true pytest backend/tests -q
cd frontend
npm ci
npm run type-check
npm run build
```

Pour le test visuel : installer Chromium avec Playwright, lancer le frontend localement, puis exécuter `python scripts/ui_smoke.py`. `RADAR_UI_BASE_URL` permet de préciser l’URL locale de test. Les captures sont produites dans `/tmp` ; les mocks ne sont pas chargés dans l’application.

## CI et statut attendu

`quality.yml` contrôle PostgreSQL + tests backend, typage et build frontend. Un job séparé `migration-history` exécute la chaîne historique sur une base vierge et **doit rendre visible le blocage hérité**, sans le convertir en succès. La PR peut être examinée ; elle ne doit pas être considérée déployable uniquement parce que les tests du nouveau code passent.

La CI GitHub elle-même n’a pas encore été observée au moment de la validation locale. Les tests ne valident pas des fournisseurs artistiques, comptes Google ou services de paiement réels.


## Complément du 20 octobre 2026

Suite backend : 69 tests passent sur PostgreSQL jetable (995 avertissements de dépréciation/configuration de test avant nettoyage de ces conventions). Correctifs et nouvelles limites : API-AUDIT.md. Vérification des parcours locaux avec le vrai backend : LOCAL-DEBUG.md. La CI précédente a été inspectée : frontend réussi ; backend échouait sur une f-string de fixture incompatible avec Python 3.11, corrigée ; migration-history échouait sur le blocage historique connu. Le nouveau résultat distant doit être vérifié après publication.


## Collecte Spotify publique — 20 octobre 2026

92 tests backend réussis, dont 23 cas supplémentaires couvrant collecte/identité, erreurs HTTP, cache, absence d’estimation, persistance et restitution de provenance. Quatre artistes vérifiés par requêtes réelles non authentifiées : voir SPOTIFY-AUDIENCE.md. Typage TypeScript, build Next.js et compilation Python réussis. Aucun nouveau schéma ni migration pour ce collecteur.
