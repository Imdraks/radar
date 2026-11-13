# Radar — parcours regroupés et navigation simplifiée

## Expérience principale

La DA « Signal clair » est conservée. La simplification porte sur les points d’entrée et les interactions : les sélections et la comparaison se trouvent dans Discovery ; le pipeline dans Clients et prospects ; les devis et factures dans une même entrée ; la carte dans les événements.

| Entrée principale | Accès contextuels | Conservation |
| --- | --- | --- |
| Discovery | Recherche et analyse ; sélections et comparaison | Recherche, fiches, enrichissement, listes et comparaisons existants |
| Événements | Production événementielle ; carte artistique | Événements, projets et cartographie existants |
| Clients et prospects | Clients et contacts ; pipeline commercial | CRM, contacts et deals existants |
| Devis et factures | Devis ; factures et paiements | Documents, statuts, numéros et suivi existants |

Les liens contextuels proviennent du catalogue backend `NAV_SECTIONS` et sont filtrés par les droits effectifs du workspace. Ils servent également à sélectionner la bonne entrée latérale sur une sous-page ou une fiche. Le raccourci mobile Discovery reste actif sur la comparaison ; Événements reste actif sur la carte. Aucun droit n’est attribué par le frontend.

Les doublons exacts Today/Cockpit/Dashboard et les recherches Artistes/Spotify Search conservent leurs redirections antérieures. Les raccourcis redondants de Discovery et le lien de carte en double ont été retirés de la présentation.

## Historique accessible

Les profils de recherche, sélections de veille, règles de scoring, échéances, leads, dossiers, briefs et anciens rapports restent accessibles via **Paramètres → Historique et outils secondaires**. Une indication apparaît sur ces anciens écrans pour orienter vers le parcours principal. Les accès sont présentés selon les fonctionnalités activées ; les API continuent d’appliquer leurs propres permissions et l’isolation des données.

Ces écrans n’utilisent pas tous les mêmes données : les analyses territoriales et les anciens profils ne sont donc pas présentés comme une fusion automatique dans Discovery. Aucun enregistrement n’est transformé, supprimé ou réattribué. Les URL existantes, les API et les composants sont conservés. Les outils de veille n’apparaissent plus dans le menu d’administration plateforme, qui garde les sources et leur état de santé.

Le wiki technique, la veille concurrentielle généraliste, les prédictions commerciales suspendues et les accès bancaires avancés ne sont pas réintroduits.

## Accueil et paramètres

L’accueil ne présente plus de blocs commerciaux aux plans Core et Premium. Les données financières manquantes restent indiquées comme absentes pour Business. Aucun budget ou indicateur fictif n’est ajouté.

Les paramètres gardent les informations réelles du compte, les notifications, la double authentification et le thème. L’espace équipe/intégrations dispose déjà de sa page dédiée : le doublon embarqué est retiré. Les commandes de sauvegarde du profil, de changement de mot de passe et de densité d’affichage ne possédaient aucun gestionnaire d’action ; elles ne sont plus affichées comme des fonctions utilisables. L’ancien customiseur de dashboard et ses composants restent dans le dépôt ; les préférences locales ne sont pas effacées.

## Mise à jour et limites

Aucune migration ni suppression de données n’est nécessaire. La navigation backend et les composants frontend doivent être mis à jour ensemble. Dans le Codespace : récupérer la branche, arrêter puis relancer les services avec `.devcontainer/radar.py`.

La présence des anciens outils dans l’historique ne certifie pas leurs intégrations externes. Leur fonctionnement et leurs permissions existants sont conservés ; la validation de ce lot porte sur la navigation, les accès et les interactions indiqués dans les tests.

## Vérifications

- **154 tests backend réussis** sur PostgreSQL jetable, dont cinq nouveaux contrôles des regroupements, des liens contextuels, des abonnements expirés et de l’isolation de workspace/rôle.
- Typage TypeScript et build Next.js réussis.
- Cinq scénarios navigateur Core/Premium/Business sur ordinateur et Business sur tablette/téléphone : onglets des six pages regroupées, entrée latérale active, accès à l’historique, retrait des commandes sans action, absence de blocs commerciaux pour Core/Premium, barre rétractable et demandes d’abonnement/Addons.
- Deux régressions de fiches artistes : profils sociaux enregistrables et rafraîchissement après enrichissement complet ou partiel.

Les réponses API des tests navigateur sont explicitement simulées. Les tests backend utilisent une vraie base jetable. La réparation de l’historique Alembic, les fournisseurs externes et les paiements réels ne sont pas nouvellement validés par ce lot.
