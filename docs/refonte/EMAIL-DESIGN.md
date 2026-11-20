# E-mails Radar : charte commune

## Messages couverts

| Parcours existant | Modèle |
| --- | --- |
| Invitation à rejoindre une équipe | `workspace_invite` |
| Premier accès avec mot de passe temporaire | `workspace_invitation` |
| Invitation / relance d’un compte existant | `workspace_invitation`, sans mot de passe |
| Récupération du mot de passe | `password_reset` |
| Code de sécurité A2F par e-mail | `mfa_code` |
| Première ouverture d’une demande par l’équipe Radar | `contact_opened` |
| Notification d’opportunités | `opportunities_detected` |
| Rapport hebdomadaire commercial | `weekly_stats` |
| Synthèse d’activité produite par le moteur de rapports | `intelligence_report` |

Le moteur de synthèse expose aussi son HTML via l’API existante : cet aperçu reprend
la charte sans créer de nouveau déclencheur d’envoi. Les PDF, SMS, notifications
Slack/Discord et calculs métier ne sont pas modifiés.

## Présentation et contenu

`backend/app/services/email_design.py` fournit un cadre de 600 px, un titre
éditorial, des cartes arrondies, un bouton violet et un pied de page commun.
`email_templates.py` compose chaque parcours à partir de données réelles. Les
champs dynamiques sont échappés, y compris dans les cartes ; seuls les liens
HTTP(S) absolus sans identifiants embarqués sont acceptés. Les jetons des liens
de récupération, y compris leur fragment, restent intacts.

Le HTML utilise des tableaux de présentation, des styles en ligne, une police
Inter lorsqu’elle est disponible avec des polices système de secours, et une
adaptation mobile. Aucun script, pixel de suivi, image distante ou chargement de
police n’est requis. Les clients qui ne prennent pas en charge les arrondis ou les
règles mobiles gardent un message lisible. Le rendu exact dans Outlook desktop,
Gmail et Apple Mail, notamment leurs modes sombres forcés, doit être recetté sur
les clients réels après déploiement ; les captures Chromium ne les émulent pas.

Les informations de sécurité restent visibles : récupération à usage unique de
15 minutes, code A2F de 5 minutes maximum, premier mot de passe de 24 heures à
remplacer obligatoirement. Les codes et mots de passe ne sont pas placés dans
l’aperçu d’objet (pré-en-tête). Les versions texte restent présentes, et SMTP
ajoute une alternative HTML aux messages transactionnels au même titre que Resend.
Les transports, règles d’activation, contrôles d’échec et identifiants
d’idempotence existants sont conservés.

Le pied de page pointe vers les vraies pages `/legal`, `/privacy` et `/terms` de
`FRONTEND_URL`. Aucune adresse légale, enquête de satisfaction ou fonction de
désabonnement fictive n’est ajoutée. Ce travail porte sur les parcours existants,
pas sur un nouveau système de campagne marketing.

## Aperçus et vérification

Depuis la racine avec les dépendances backend installées :

```bash
PYTHONPATH=backend TESTING=true python scripts/email_preview.py
PYTHONPATH=backend TESTING=true python scripts/email_ui_smoke.py
```

Les fichiers HTML et les captures sont écrits dans `/tmp/radar-email-previews`.
`email_preview.py` utilise uniquement des données d’exemple et n’envoie rien.
Ouvrir `index.html` pour parcourir les neuf messages. Le test navigateur utilise
Playwright Chromium et vérifie 800, 390 et 320 px, l’absence de débordement et de
requêtes externes. La CI produit l’artefact `radar-email-previews` pour examen.

Les tests backend vérifient également les contenus dynamiques hostiles, la
conservation des données de rapports, les liens, les durées de sécurité et les
adaptateurs SMTP/Resend simulés. Aucun message réel n’est envoyé par les tests.

## Déploiement

Aucune migration ou nouvelle variable d’environnement. `FRONTEND_URL` doit être
l’URL publique correcte. Reconstruire et relancer backend, worker et scheduler
pour que les prochains messages utilisent les nouveaux modèles. Les messages déjà
reçus ne changent pas. Resend et le domaine expéditeur doivent rester configurés
et vérifiés, ou le SMTP existant doit être opérationnel.
