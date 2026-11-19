"""
Public contact form endpoint (no auth required)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Literal
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models.contact_inquiry import ContactInquiry
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])


CONTACT_NOTICE_VERSION = "2026-11-13"


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=150, pattern=r"^[^\r\n]+$")
    email: EmailStr
    company: str = Field(default="", max_length=200, pattern=r"^[^\r\n]*$")
    phone: str = Field(default="", max_length=40, pattern=r"^[^\r\n]*$")
    plan: Literal["", "core", "premium", "business", "custom"] = ""
    message: str = Field(min_length=5, max_length=5000)
    privacy_notice_version: Literal["2026-11-13"]


@router.post("")
async def submit_contact(data: ContactRequest, db: Session = Depends(get_db)):
    """Acknowledge only a committed request; submission sends no email."""
    request_id = uuid4()
    row = ContactInquiry(
        id=request_id,
        **data.model_dump(),
        status="new",
        acknowledgement_status="not_requested"
    )
    try:
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        reference = uuid4().hex[:12]
        logger.warning("contact_persistence_failed reference=%s", reference)
        raise HTTPException(
            503, detail={"code": "CONTACT_UNAVAILABLE", "reference": reference}
        ) from None
    return {
        "status": "ok",
        "reference": str(request_id),
        "message": "Votre demande est enregistrée dans Radar.",
    }
