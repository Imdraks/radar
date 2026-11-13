"""Transport boundary for a future accredited e-invoicing provider.

No provider is configured or simulated. PDF/manual tracking never implies transmission.
"""

from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True)
class SubmissionReceipt:
    provider: str
    transmission_id: str
    status: str


class ElectronicInvoiceTransport(Protocol):
    def submit(
        self, *, document_id: str, structured_document: bytes, idempotency_key: str
    ) -> SubmissionReceipt: ...
    def status(self, transmission_id: str) -> SubmissionReceipt: ...


def capabilities():
    return {
        "electronic_transmission_available": False,
        "validated_provider": None,
        "payment_confirmation": "manual_declaration",
        "message": "Aucune transmission à une plateforme agréée n’est activée. Les paiements sont déclarés manuellement.",
    }
