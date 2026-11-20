"""Radar email families. Rendering only: no provider call or new delivery trigger."""

from app.services.email_design import render_email, card, credential, paragraph, app_url


def workspace_invite(email, workspace, inviter=None, role="member"):
    roles = {
        "admin": "Administrateur",
        "member": "Membre",
        "viewer": "Lecture seule",
        "owner": "Responsable",
    }
    return render_email(
        title="Votre équipe vous attend.",
        intro=f"Vous êtes invité à rejoindre {workspace} sur Radar.",
        eyebrow="Invitation",
        body=card(
            "Un espace pour avancer ensemble.",
            "Retrouvez les projets, les fichiers et les échanges de votre équipe.",
            rows=[
                ("Espace de travail", workspace),
                ("Adresse de connexion", email),
                ("Rôle attribué", roles.get(role, role)),
            ]
            + ([("Invitation de", inviter)] if inviter else []),
        ),
        cta=("Rejoindre mon espace", app_url("/login")),
        note="Connectez-vous avec cette adresse et une méthode de connexion disponible pour votre compte. Si cette invitation était inattendue, contactez votre interlocuteur Radar.",
    )


def workspace_invitation(email, workspace, password=None):
    body = card(
        "Vos informations de connexion",
        rows=[("Espace de travail", workspace), ("Adresse e-mail", email)],
    )
    if password:
        body += credential(password, "Mot de passe temporaire")
        body += card(
            "Un premier accès, à votre rythme.",
            rows=[
                (
                    "1 · Choisissez votre mot de passe",
                    "Le mot de passe temporaire expire dans 24 heures. Son remplacement est obligatoire dès votre première connexion.",
                ),
                (
                    "2 · Renforcez votre sécurité",
                    "Configurez l’A2F ou une clé d’accès. Vous pouvez aussi choisir « Plus tard ».",
                ),
            ],
        )
    else:
        body += paragraph(
            "Utilisez vos identifiants Radar habituels ou votre fournisseur de connexion déjà associé. Votre mot de passe et votre A2F restent inchangés."
        )
    return render_email(
        title="Bienvenue dans votre espace.",
        intro=f"Votre espace {workspace} est prêt à vous accueillir.",
        eyebrow="Invitation Radar",
        body=body,
        cta=("Ouvrir Radar", app_url("/login")),
        note="Ne transmettez pas ce message. Si vous n’attendiez pas cette invitation, contactez votre interlocuteur Radar.",
    )


def password_reset(url):
    return render_email(
        title="Réinitialisez votre mot de passe.",
        intro="Une réinitialisation du mot de passe de votre compte Radar a été demandée.",
        eyebrow="Sécurité du compte",
        body=card(
            "15 minutes pour agir.",
            "Ce lien expire dans 15 minutes et ne fonctionne qu’une fois. Votre A2F reste active.",
        ),
        cta=("Choisir mon mot de passe", url),
        note="Vous n’êtes pas à l’origine de cette demande ? Ignorez ce message : votre mot de passe ne sera pas modifié.",
    )


def mfa_code(code):
    return render_email(
        title="C’est bien vous ?",
        intro="Utilisez ce code pour confirmer l’opération demandée sur votre compte Radar.",
        eyebrow="Vérification de sécurité",
        body=credential(code, "Votre code de sécurité"),
        preheader="Votre code de sécurité Radar est disponible. Validité : 5 minutes au maximum.",
        note="Ce code expire dans 5 minutes au maximum. Ne le communiquez à personne. Si vous n’avez pas demandé ce code, ignorez ce message.",
    )


def contact_opened(name, reference):
    return render_email(
        title="Votre demande est entre de bonnes mains.",
        intro=f"Bonjour {name}, notre équipe a bien ouvert votre demande.",
        eyebrow="Votre demande Radar",
        body=card(
            "La prochaine étape : échanger.",
            "Nous vous contacterons prochainement pour la traiter.",
            rows=[("Référence de votre demande", reference)],
        ),
        note="Ce message confirme l’ouverture de votre demande. Il ne constitue ni une acceptation de commande ni une confirmation de paiement.",
    )


def opportunities_detected(items):
    body = "".join(
        card(
            item["title"],
            item["organization"],
            rows=[
                ("Score enregistré", item["score"]),
                (
                    "Échéance et budget",
                    (item["deadline"] + item["budget"]).strip(" |") or "Non renseignés",
                ),
            ],
        )
        + paragraph_link("Consulter cette opportunité", item["app_url"])
        for item in items
    )
    return render_email(
        title="De nouvelles pistes à explorer.",
        intro=f"{len(items)} nouvelle(s) opportunité(s) détectée(s) dans Radar.",
        eyebrow="Votre activité",
        body=body,
        category="rapport",
    )


def paragraph_link(label, url):
    from app.services.email_design import e, link_url

    return f'<p style="margin:0 0 28px;font-size:14px;line-height:1.7;"><a href="{link_url(url)}" style="color:#5940B0;font-weight:600;">{e(label)} →</a></p>'


def weekly_stats(stats):
    money = lambda value: f"{value:,.0f} €".replace(",", " ")
    body = card(
        "L’essentiel de la semaine",
        rows=[
            ("Nouvelles opportunités", stats.total_new),
            ("Qualifiées", stats.total_qualified),
            ("Candidatures déposées", stats.total_submitted),
            ("Gagnées", stats.total_won),
            ("Perdues", stats.total_lost),
            ("Taux de conversion calculé", f"{stats.conversion_rate:.1f} %"),
            ("Score moyen des nouvelles", f"{stats.avg_score_new:.1f}"),
        ],
    )
    changes = [
        (label, f"{stats.vs_previous_week[key]:+.1f} %")
        for key, label in [
            ("new_change", "Nouvelles opportunités / semaine précédente"),
            ("won_change", "Gagnées / semaine précédente"),
        ]
        if key in stats.vs_previous_week
    ]
    if changes:
        body += card("Évolution calculée", rows=changes)
    body += card(
        "Votre suivi financier",
        rows=[
            ("Budget gagné sur la période", money(stats.budget_won)),
            ("Budget du pipeline", money(stats.budget_pipeline)),
            ("Budget moyen", money(stats.avg_budget)),
        ],
    )
    body += paragraph("Opportunités à suivre")
    for item in stats.top_opportunities:
        body += card(
            item["title"],
            rows=[
                ("Score enregistré", f"{item['score']}/20"),
                (
                    "Budget",
                    (
                        money(item["budget"])
                        if item["budget"] is not None
                        else "Non renseigné"
                    ),
                ),
                (
                    "Échéance",
                    (
                        str(item["deadline"])[:10]
                        if item["deadline"]
                        else "Non renseignée"
                    ),
                ),
            ],
        )
    if not stats.top_opportunities:
        body += paragraph("Aucune opportunité à présenter pour cette période.")
    body += paragraph("Échéances des 7 prochains jours")
    for item in stats.urgent_deadlines:
        body += card(
            item["title"],
            rows=[
                ("Jours restants", item["days_remaining"]),
                ("État enregistré", item["status"]),
            ],
        )
    if not stats.urgent_deadlines:
        body += paragraph("Aucune échéance urgente enregistrée.")
    return render_email(
        title="Votre semaine, en perspective.",
        intro=f"Du {stats.period_start:%d/%m/%Y} au {stats.period_end:%d/%m/%Y}.",
        eyebrow="Rapport hebdomadaire",
        body=body,
        cta=("Retrouver mon activité", app_url()),
        category="rapport",
        note="Ces chiffres proviennent des données enregistrées dans Radar sur la période du rapport.",
    )


def intelligence_report(
    start, end, metrics, highlights, top, upcoming, recommendations
):
    body = "".join(card(h["title"], h["description"]) for h in highlights)
    body += card(
        "Les indicateurs de la période",
        rows=[
            ("Nouvelles opportunités", metrics["new_count"]),
            ("Opportunités à score élevé", metrics["high_score_count"]),
            ("Taux de conversion calculé", f"{metrics['conversion_rate']} %"),
        ],
    )
    body += paragraph("Opportunités à suivre")
    for item in top[:5]:
        body += card(
            item.get("title", "Titre non renseigné"),
            item.get("organization") or "Organisation non renseignée",
            rows=[
                (
                    "Score enregistré",
                    (
                        f"{item['score']}/10"
                        if item.get("score") is not None
                        else "Non renseigné"
                    ),
                )
            ],
        )
    if not top:
        body += paragraph("Aucune opportunité à présenter pour cette période.")
    body += paragraph("Les prochaines échéances")
    for item in upcoming[:5]:
        body += card(
            item.get("title", "Titre non renseigné"),
            rows=[
                ("Jours restants", item.get("days_until_deadline", "Non renseignés"))
            ],
        )
    if not upcoming:
        body += paragraph("Aucune échéance à présenter pour cette période.")
    for item in recommendations:
        body += card("Piste d’action", item)
    return render_email(
        title="Gardez le cap sur votre activité.",
        intro=f"Du {start:%d/%m/%Y} au {end:%d/%m/%Y}.",
        eyebrow="Votre synthèse Radar",
        body=body,
        cta=("Ouvrir Radar", app_url()),
        category="rapport",
        note="Les scores et recommandations sont des aides à l’analyse, pas des garanties de résultat.",
    )
