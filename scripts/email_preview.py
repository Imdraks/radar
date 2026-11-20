"""Render every Radar mail family locally. No email is sent; all values are fixtures."""

import argparse
from datetime import datetime
from decimal import Decimal
from html import escape
from pathlib import Path
from app.services import email_templates as t
from app.services.weekly_report_service import WeeklyStats, WeeklyReportService
from app.intelligence.weekly_report import WeeklyReportGenerator


def previews():
    start, end = datetime(2026, 11, 16), datetime(2026, 11, 23)
    stats = WeeklyStats(
        period_start=start,
        period_end=end,
        total_new=12,
        total_qualified=4,
        total_won=1,
        budget_won=Decimal("2400"),
        budget_pipeline=Decimal("4800"),
        avg_budget=Decimal("1200"),
        conversion_rate=12.5,
        top_opportunities=[
            dict(
                title="EXEMPLE — Production d’un événement",
                score=14,
                budget=2400,
                deadline="2026-11-25",
            )
        ],
        urgent_deadlines=[
            dict(
                title="EXEMPLE — Dossier de production",
                days_remaining=3,
                status="En préparation",
            )
        ],
    )
    return {
        "invitation": t.workspace_invite(
            "client@example.com", "Studio Exemple", "Camille", "admin"
        ),
        "premiere-connexion": t.workspace_invitation(
            "client@example.com", "Studio Exemple", "EXEMPLE-Aa1!-non-valide"
        ),
        "invitation-compte-existant": t.workspace_invitation(
            "client@example.com", "Studio Exemple"
        ),
        "mot-de-passe": t.password_reset(
            "https://example.com/reset-password#token=EXEMPLE-NON-VALIDE"
        ),
        "code-a2f": t.mfa_code("123456"),
        "demande-ouverte": t.contact_opened("Camille", "EXEMPLE-2026-001"),
        "opportunites": t.opportunities_detected(
            [
                dict(
                    title="EXEMPLE — Une nouvelle production",
                    organization="Studio Exemple",
                    score=12,
                    deadline=" | Échéance : 25/11/2026",
                    budget=" | Budget : 2 400 €",
                    app_url="https://example.com/opportunities/example",
                )
            ]
        ),
        "rapport-hebdomadaire": WeeklyReportService(None).generate_html_report(stats),
        "synthese-activite": WeeklyReportGenerator()._generate_html(
            start,
            end,
            dict(new_count=12, high_score_count=4, conversion_rate=12.5),
            [
                dict(
                    title="EXEMPLE — Votre activité avance",
                    description="12 nouvelles opportunités sur la période.",
                )
            ],
            [],
            [
                dict(
                    title="EXEMPLE — Production d’un événement",
                    organization="Studio Exemple",
                    score=8,
                )
            ],
            [],
            ["Vérifiez les prochaines échéances avant de préparer vos dossiers."],
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/radar-email-previews")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    mails = previews()
    for name, html in mails.items():
        (args.output / (name + ".html")).write_text(html, encoding="utf-8")
    links = "".join(
        f'<li><a href="{escape(name)}.html">{escape(name)}</a></li>' for name in mails
    )
    (args.output / "index.html").write_text(
        '<!doctype html><html lang="fr"><meta charset="utf-8"><title>Radar — Aperçus e-mails</title><body style="font:18px Arial;padding:32px;background:#F5F4F9;color:#202033"><h1>Radar. Les e-mails</h1><p>Aperçus locaux · Données d’exemple uniquement · Aucun envoi</p><ul>'
        + links
        + "</ul></body></html>",
        encoding="utf-8",
    )
    print(f"{len(mails)} aperçus générés dans {args.output} — aucun e-mail envoyé.")


if __name__ == "__main__":
    main()
