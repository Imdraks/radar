"""Provider-neutral handover, explicitly not Factur-X/UBL certification or PA transmission."""

import hashlib
import json
from decimal import Decimal
from fastapi import HTTPException
from app.services.invoice_lifecycle import frozen_parties

FISCAL_EMITTER = (
    "legal_name",
    "forme_juridique",
    "capital_social",
    "rcs_city",
    "siret",
    "vat_number",
    "legal_address",
    "legal_postal_code",
    "legal_city",
    "legal_country",
)
FISCAL_CUSTOMER = (
    "name",
    "company_name",
    "siret",
    "vat_number",
    "address_line1",
    "address_line2",
    "postal_code",
    "city",
    "country",
)


def exchange(invoice, workspace):
    if not invoice.issued_at:
        raise HTTPException(
            409, "Émettre la facture avant de préparer son dossier de transmission"
        )
    emitter, customer = frozen_parties(invoice, workspace)
    data = {
        "format": "radar-invoice-exchange-v1",
        "regulated_format": False,
        "transmission_status": "not_transmitted",
        "provider_connected": False,
        "currency": "EUR",
        "invoice_id": invoice.id,
        "reference": invoice.reference,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "issuer": {key: getattr(emitter, key, None) for key in FISCAL_EMITTER},
        "customer": {key: getattr(customer, key, None) for key in FISCAL_CUSTOMER},
        "legal_details": invoice.legal_details,
        "amounts": {
            key: str(getattr(invoice, key))
            for key in (
                "subtotal",
                "discount_percent",
                "discount_amount",
                "tax_rate",
                "tax_amount",
                "total",
            )
        },
        "items": [
            {
                key: str(getattr(item, key))
                for key in (
                    "description",
                    "quantity",
                    "unit",
                    "unit_price",
                    "line_total",
                    "position",
                )
            }
            for item in invoice.items
        ],
        "credited_at": invoice.credited_at.isoformat() if invoice.credited_at else None,
        "limitations": [
            "A platform-approved adapter, regulated format validation, scope determination and actual transmission are required.",
            "This dossier is not a payment receipt, delivery acknowledgment or regulatory invoice transmission.",
        ],
    }
    data["sha256"] = hashlib.sha256(
        json.dumps(
            data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return data
