"""Downloadable Radar quote PDFs. Document values come only from persisted snapshots."""

from io import BytesIO
from datetime import timezone
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def render_quote_pdf(quote):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=36,
        bottomMargin=40,
        title=quote.reference,
        author=quote.issuer["name"],
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="RadarTitle",
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=32,
            textColor=colors.HexColor("#7050DC"),
            spaceAfter=12,
        )
    )
    styles.add(ParagraphStyle(name="RadarSmall", fontSize=9, leading=14))
    styles.add(
        ParagraphStyle(name="RadarRight", fontSize=10, leading=16, alignment=TA_RIGHT)
    )

    def p(text, style="RadarSmall"):
        return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), styles[style])

    def money(value):
        return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " EUR"

    issuer = quote.issuer
    buyer = quote.buyer
    created = quote.created_at.replace(tzinfo=timezone.utc).astimezone(
        ZoneInfo("Europe/Paris")
    )
    elements = [
        Paragraph("RADAR · DEVIS", styles["RadarTitle"]),
        p(quote.reference, "Heading2"),
        p("Brouillon" if quote.status == "draft" else "Devis émis"),
        p(
            f"Créé le {created:%d/%m/%Y} · valable jusqu’au {quote.valid_until:%d/%m/%Y}"
        ),
        Spacer(1, 22),
    ]
    left = "\n".join(
        filter(
            None,
            [
                issuer.get("name"),
                issuer.get("legal_form"),
                issuer.get("address"),
                "SIRET : " + issuer.get("siret", ""),
                issuer.get("registration"),
                (
                    ("TVA : " + issuer.get("vat_number"))
                    if issuer.get("vat_number")
                    else None
                ),
                issuer.get("email"),
                issuer.get("phone"),
            ],
        )
    )
    right = "\n".join(
        filter(
            None,
            [
                buyer.get("name"),
                buyer.get("address"),
                " ".join(filter(None, [buyer.get("postal_code"), buyer.get("city")])),
                buyer.get("country"),
                ("SIRET : " + buyer.get("siret")) if buyer.get("siret") else None,
                buyer.get("email"),
            ],
        )
    )
    parties = Table(
        [[p("ÉMETTEUR"), p("CLIENT")], [p(left), p(right)]], colWidths=[257, 257]
    )
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements += [parties, Spacer(1, 22)]
    rows = [[p("Prestation"), p("Qté"), p("Prix unitaire HT"), p("TVA"), p("Total HT")]]
    for line in quote.lines:
        from decimal import Decimal

        rows.append(
            [
                p(line["description"]),
                p(line["quantity"]),
                p(money(Decimal(line["unit_price"]))),
                p(line["vat_rate"] + " %"),
                p(money(Decimal(line["total_ht"]))),
            ]
        )
    table = Table(rows, colWidths=[205, 38, 105, 48, 118], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0EBFF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#DDD4F7")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#E8E5EF")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements += [
        table,
        Spacer(1, 18),
        p("Total HT : " + money(quote.total_ht), "RadarRight"),
        p("TVA : " + money(quote.total_tax), "RadarRight"),
        p("Total TTC : " + money(quote.total_ttc), "RadarRight"),
        Spacer(1, 20),
    ]
    if quote.notes:
        elements += [
            p("Conditions et précisions", "Heading3"),
            p(quote.notes),
            Spacer(1, 18),
        ]
    elements += [
        p(
            "Ce document est un devis, pas une facture ni une confirmation de paiement. L’activation des services suit la validation de la commande et des pièces contractuelles."
        ),
        p("Référence à rappeler : " + quote.reference),
    ]
    doc.build(elements)
    return buffer.getvalue()
