"""Shared, image-free email design. Dynamic text and links must use these helpers."""

from html import escape
from urllib.parse import urlsplit
from app.core.config import settings

PURPLE = "#704CE6"
INK = "#202033"
MUTED = "#66667D"


def e(value):
    return escape(str(value), quote=True)


def link_url(value):
    """Keep query/fragment tokens intact; reject active or malformed URL schemes."""
    value = str(value)
    parts = urlsplit(value)
    if (
        parts.scheme not in {"https", "http"}
        or not parts.netloc
        or parts.username
        or parts.password
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("Email links require an absolute HTTP(S) URL")
    return e(value)


def app_url(path=""):
    return settings.frontend_url.rstrip("/") + path


def paragraph(text):
    return f'<p style="margin:0 0 18px;font-size:16px;line-height:1.65;color:{INK};overflow-wrap:anywhere;">{e(text)}</p>'


def card(title, text="", rows=()):
    details = "".join(
        f'<tr><td style="padding:9px 0;border-top:1px solid #ECE9F3;font-size:14px;line-height:1.6;color:{MUTED};">{e(label)}<br><strong style="color:{INK};font-weight:600;word-break:break-word;">{e(value)}</strong></td></tr>'
        for label, value in rows
    )
    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 20px;border:1px solid #E7E3EF;border-radius:20px;border-collapse:separate;background:#FFFFFF;"><tr><td style="padding:24px;"><h2 style="margin:0 0 10px;color:{INK};font-size:21px;line-height:1.3;font-weight:700;">{e(title)}</h2>{paragraph(text) if text else ""}<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{details}</table></td></tr></table>'


def credential(value, label):
    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:24px 0;background:#F3EFFF;border-radius:18px;"><tr><td style="padding:24px;text-align:center;"><p style="margin:0 0 12px;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#5940B0;">{e(label)}</p><p dir="ltr" style="margin:0;font-family:Consolas,monospace;font-size:26px;line-height:1.5;font-weight:700;color:{INK};word-break:break-all;">{e(value)}</p></td></tr></table>'


def render_email(
    *,
    title,
    intro,
    body="",
    cta=None,
    eyebrow="Votre espace Radar",
    preheader="",
    note="",
    category="transactionnel",
):
    """Table layout and inline styles work without webfonts, JS or remote images.

    body is composed only from escaped helpers; never insert user-supplied HTML.
    """
    home = app_url()
    button = ""
    if cta:
        label, url = cta
        href = link_url(url)
        button = f'<table role="presentation" cellspacing="0" cellpadding="0" style="margin:28px auto;"><tr><td bgcolor="{PURPLE}" style="border-radius:28px;text-align:center;mso-padding-alt:16px 28px;"><a href="{href}" style="display:inline-block;padding:16px 28px;border:1px solid {PURPLE};border-radius:28px;background:{PURPLE};color:#FFFFFF;font-size:16px;font-weight:600;line-height:1.35;text-decoration:none;">{e(label)}</a></td></tr></table><p style="margin:0 0 24px;font-size:12px;line-height:1.7;color:{MUTED};text-align:center;">Si le bouton ne fonctionne pas, <a href="{href}" style="color:#5940B0;text-decoration:underline;">ouvrez ce lien</a>.</p>'
    reason = (
        "Cet e-mail concerne la sécurité ou le fonctionnement de votre compte Radar."
        if category == "transactionnel"
        else "Ce rapport correspond aux notifications d’activité configurées dans Radar."
    )
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"><title>{e(title)}</title>
<style>body,table,td,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}table{{mso-table-lspace:0;mso-table-rspace:0;}}@media only screen and (max-width:600px){{.outer{{padding:12px 8px!important;}}.content{{padding:30px 20px!important;}}.headline{{font-size:30px!important;}}.footer{{padding:24px 20px!important;}}}}</style></head>
<body style="margin:0;padding:0;background:#F5F4F9;color:{INK};font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">{e(preheader or intro)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#F5F4F9"><tr><td class="outer" align="center" style="padding:36px 16px;">
<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;table-layout:fixed;background:#FFFFFF;border:1px solid #E7E3EF;border-radius:28px;border-collapse:separate;"><tr><td class="content" style="padding:44px 40px 32px;">
<p style="margin:0 0 36px;text-align:center;"><a href="{link_url(home)}" style="font-size:30px;font-weight:750;letter-spacing:-1.2px;color:{INK};text-decoration:none;">Radar<span style="color:{PURPLE};">.</span></a></p>
<p style="margin:0 0 14px;text-align:center;color:#5940B0;font-size:11px;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;">{e(eyebrow)}</p>
<h1 class="headline" style="margin:0 0 20px;text-align:center;font-size:38px;line-height:1.12;letter-spacing:-1.2px;font-weight:750;color:{INK};">{e(title)}</h1>
<p style="margin:0 0 28px;text-align:center;font-size:17px;line-height:1.65;color:{MUTED};overflow-wrap:anywhere;">{e(intro)}</p>
{body}{button}
{f'<p style="margin:24px 0 0;padding:18px;border-radius:14px;background:#F8F7FB;color:{MUTED};font-size:13px;line-height:1.7;">{e(note)}</p>' if note else ''}
</td></tr><tr><td class="footer" style="padding:28px 40px;background:#F0EEF6;border-radius:0 0 27px 27px;">
<p style="margin:0 0 12px;font-size:21px;font-weight:700;color:{INK};">Radar<span style="color:{PURPLE};">.</span></p><p style="margin:0 0 14px;font-size:13px;line-height:1.7;color:{MUTED};">Le point de repère de votre agence.<br>{e(reason)}</p>
<p style="margin:0;font-size:12px;line-height:2;"><a href="{link_url(app_url('/legal'))}" style="color:#5940B0;">Mentions légales</a> &nbsp;·&nbsp; <a href="{link_url(app_url('/privacy'))}" style="color:#5940B0;">Confidentialité</a> &nbsp;·&nbsp; <a href="{link_url(app_url('/terms'))}" style="color:#5940B0;">Conditions</a></p>
</td></tr></table><!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>"""
