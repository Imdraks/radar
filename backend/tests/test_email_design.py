"""Mail content and actual MIME/provider adapters, without real delivery."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from app.core.config import settings
from app.services import email_templates as t
from app.services.email_design import link_url
from app.services.weekly_report_service import WeeklyStats, WeeklyReportService
from app.intelligence.weekly_report import WeeklyReportGenerator

EVIL = '<img src=x onerror="alert(1)"> & Agence'


def documents():
    start = datetime(2026, 11, 20)
    return [
        t.workspace_invite("client@example.com", EVIL, EVIL, "admin"),
        t.workspace_invitation("client@example.com", EVIL, "TEMP-Aa1!"),
        t.workspace_invitation("client@example.com", EVIL),
        t.password_reset("https://example.com/reset-password#token=abc&state=def"),
        t.mfa_code("123456"),
        t.contact_opened(EVIL, "TEST-42"),
        t.opportunities_detected(
            [
                dict(
                    title=EVIL,
                    organization=EVIL,
                    score=10,
                    deadline="",
                    budget="",
                    app_url="https://example.com/opportunities/42",
                )
            ]
        ),
        WeeklyReportService(None).generate_html_report(
            WeeklyStats(
                period_start=start,
                period_end=start,
                top_opportunities=[
                    dict(title=EVIL, budget=None, deadline=None, score=12)
                ],
            )
        ),
        WeeklyReportGenerator()._generate_html(
            start,
            start,
            dict(new_count=1, high_score_count=0, conversion_rate=0),
            [dict(title=EVIL, description=EVIL)],
            [],
            [dict(title=EVIL, organization=EVIL, score=2)],
            [dict(title=EVIL, days_until_deadline=3)],
            [EVIL],
        ),
    ]


@pytest.mark.parametrize("index", range(9))
def test_every_family_is_branded_accessible_and_escaped(index):
    html = documents()[index]
    assert '<html lang="fr">' in html
    assert 'name="viewport"' in html
    assert "#704CE6" in html and "Radar<span" in html
    assert 'role="presentation"' in html
    assert "/privacy" in html and "/legal" in html and "/terms" in html
    assert "<script" not in html and "<img" not in html
    assert 'onerror="' not in html
    assert "display: grid" not in html and "display:flex" not in html
    assert "Se désabonner" not in html and "Pas utile" not in html


def test_security_content_and_preheaders_keep_real_validities():
    from html import unescape

    reset = t.password_reset("https://example.com/reset-password#token=abc&state=def")
    assert "15 minutes" in reset and "qu’une fois" in reset and "A2F" in reset
    assert "https://example.com/reset-password#token=abc&state=def" in unescape(reset)
    code = t.mfa_code("123456")
    assert "5 minutes" in code and "123456" in code
    assert "123456" not in code.split('<div style="display:none')[1].split("</div>")[0]
    invitation = t.workspace_invitation("client@example.com", "Studio", "TEMP-Aa1!")
    assert "24 heures" in invitation and "TEMP-Aa1!" in invitation
    assert "A2F" in invitation and "Plus tard" in invitation
    assert (
        "TEMP-Aa1!"
        not in invitation.split('<div style="display:none')[1].split("</div>")[0]
    )
    assert "TEMP-Aa1!" not in t.workspace_invitation("client@example.com", "Studio")


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,unsafe",
        "//evil.example",
        "https://user:secret@example.com",
        "https://example.com/\nunsafe",
    ],
)
def test_unsafe_button_urls_rejected(url):
    with pytest.raises(ValueError):
        link_url(url)


def test_smtp_alternative_retains_text_and_transport_security(monkeypatch):
    from app.services.mfa_delivery import smtp_send

    sent = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            sent.append("tls")

        def login(self, *args):
            sent.append("login")

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr("app.services.mfa_delivery.smtplib.SMTP", SMTP)
    monkeypatch.setattr(settings, "smtp_port", 587)
    smtp_send(
        "client@example.com", "Code : 123456", "Sécurité Radar", t.mfa_code("123456")
    )
    assert sent[:2] == ["tls", "login"]
    message = sent[2]
    assert message.get_content_type() == "multipart/alternative"
    assert "Code : 123456" in message.get_body(preferencelist=("plain",)).get_content()
    assert "#704CE6" in message.get_body(preferencelist=("html",)).get_content()


@pytest.mark.parametrize("method", ["resend", "smtp"])
def test_security_delivery_uses_same_design_in_both_adapters(monkeypatch, method):
    from app.services.mfa_delivery import deliver
    from app.services.password_email import send_reset_link

    monkeypatch.setattr(
        settings, "resend_api_key", "TEST-no-real-key" if method == "resend" else ""
    )
    monkeypatch.setattr(
        "app.services.mfa_delivery.availability", lambda: {"email": True}
    )
    monkeypatch.setattr(
        "app.services.password_email.availability", lambda: {"email": True}
    )
    mail = AsyncMock(return_value={"id": "TEST-accepted"})
    monkeypatch.setattr("app.services.email_service.EmailService.send_email", mail)
    smtp = []
    monkeypatch.setattr(
        "app.services.mfa_delivery.smtp_send", lambda *args: smtp.append(args)
    )
    monkeypatch.setattr(
        "app.services.password_email.smtp_send", lambda *args: smtp.append(args)
    )
    asyncio.run(deliver("email", "client@example.com", "123456"))
    asyncio.run(
        send_reset_link(
            "client@example.com", "https://example.com/reset-password#token=TEST"
        )
    )
    if method == "resend":
        assert mail.await_count == 2 and smtp == []
        for call in mail.call_args_list:
            assert "#704CE6" in call.args[2]
            assert call.args[3] and "<html" not in call.args[3]
    else:
        mail.assert_not_called()
        assert len(smtp) == 2
        for args in smtp:
            assert "#704CE6" in args[3] and "<html" not in args[1]


def test_invite_provider_receives_branded_html_and_plain_text(monkeypatch):
    from app.services.email_service import EmailService

    service = EmailService()
    mail = AsyncMock(return_value={"id": "TEST-accepted"})
    monkeypatch.setattr(service, "send_email", mail)
    asyncio.run(
        service.send_workspace_invite("client@example.com", EVIL, "Camille", "admin")
    )
    args = mail.call_args.kwargs
    assert "#704CE6" in args["html"]
    assert "<img" not in args["html"]
    assert EVIL in args["text"]
    assert "Google" not in args["text"]


@pytest.mark.parametrize("html", documents())
def test_every_family_has_shared_design_and_escapes_dynamic_content(html):
    assert '<html lang="fr">' in html
    assert "#704CE6" in html
    assert 'role="presentation"' in html
    assert "/privacy" in html and "/legal" in html and "/terms" in html
    assert "<img src=x" not in html
    assert "<script" not in html
    assert "display: grid" not in html
    assert "<script" not in html and "<iframe" not in html
    assert len(html.encode("utf-8")) < 100 * 1024


def test_reports_preserve_recorded_values_without_placeholder_statistics():
    start = datetime(2026, 11, 20)
    stats = WeeklyStats(
        period_start=start,
        period_end=start,
        total_new=37,
        total_won=4,
        vs_previous_week={"new_change": -25},
        top_opportunities=[{"title": EVIL, "budget": 0, "deadline": None, "score": 13}],
        urgent_deadlines=[],
    )
    html = WeeklyReportService(None).generate_html_report(stats)
    assert "37" in html and "13/20" in html and "-25.0 %" in html
    assert "0 €" in html
    assert "Aucune échéance urgente enregistrée" in html
    assert "&lt;img" in html
    report = WeeklyReportGenerator()._generate_html(
        start,
        start,
        {"new_count": 37, "high_score_count": 4, "conversion_rate": 12.5},
        [],
        [],
        [{"title": EVIL, "organization": EVIL, "score": 8}],
        [],
        [EVIL],
    )
    assert "&lt;img" in report and "<img src=x" not in report
    assert "37" in report and "8/10" in report
