"""
Contact Finder API - Web Enrichment for Missing Contacts
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import time
import re
import logging
import socket
from ipaddress import ip_address

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import Opportunity, ContactFinderResult
from app.api.deps import get_current_user
from app.schemas.radar_features import (
    ContactFinderRequest,
    ContactFinderResponse,
)

router = APIRouter(prefix="/contact-finder", tags=["contact-finder"])
logger = logging.getLogger(__name__)


def is_safe_url(url: str) -> bool:
    """Block SSRF: reject private IPs, localhost, metadata endpoints"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        
        # Block non-HTTP schemes
        if parsed.scheme not in ("http", "https"):
            return False
        
        # Block known dangerous hosts
        blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0", ""}
        if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
            return False
        if hostname in blocked_hosts:
            return False
        
        # Resolve hostname and check IP
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in resolved:
                ip = ip_address(sockaddr[0])
                if not ip.is_global:
                    return False
        except (socket.gaierror, ValueError):
            return False
        
        return True
    except Exception:
        return False

# Allowed domains for contact search (whitelist)
DEFAULT_ALLOWED_DOMAINS = [
    # Official/Government
    ".gouv.fr",
    ".gov",
    ".europa.eu",
    # Cultural/Music
    ".culture.fr",
    ".sacem.fr",
    ".cnm.fr",
    # Common contact pages
    "contact",
    "about",
    "team",
    "equipe",
]

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 10


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    # Filter out common fake emails
    filtered = [e for e in emails if not any(x in e.lower() for x in ['example', 'test', 'noreply', 'no-reply'])]
    return list(set(filtered))


def extract_phones(text: str) -> List[str]:
    """Extract phone numbers from text (French format)"""
    patterns = [
        r'(?:\+33|0033|0)[1-9](?:[\s.-]?\d{2}){4}',
        r'\d{2}[\s.-]\d{2}[\s.-]\d{2}[\s.-]\d{2}[\s.-]\d{2}',
    ]
    phones = []
    for pattern in patterns:
        phones.extend(re.findall(pattern, text))
    return list(set(phones))


def search_official_website(url: str, allowed_domains: List[str], max_pages: int = 5) -> dict:
    """
    Search official website for contact info.
    Returns dict with contact info and evidence.
    
    NOTE: This is a simplified version. In production, use httpx/aiohttp
    with proper rate limiting and error handling.
    """
    import httpx
    
    result = {
        "found": False,
        "email": None,
        "phone": None,
        "name": None,
        "evidence_url": None,
        "evidence_snippet": None,
        "pages_crawled": 0,
        "searched_urls": [],
    }
    
    if not url:
        return result
    
    # SSRF protection
    if not is_safe_url(url):
        logger.warning(f"SSRF blocked: {url}")
        return result
    
    try:
        # Parse base domain
        from urllib.parse import urlparse, urljoin
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # URLs to check (priority order)
        urls_to_check = [
            url,  # Original URL
            urljoin(base_url, "/contact"),
            urljoin(base_url, "/contact.html"),
            urljoin(base_url, "/contact-us"),
            urljoin(base_url, "/nous-contacter"),
            urljoin(base_url, "/about"),
            urljoin(base_url, "/a-propos"),
            urljoin(base_url, "/team"),
            urljoin(base_url, "/equipe"),
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RadarBot/1.0; +https://radarapp.fr/bot)"
        }
        
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            for check_url in urls_to_check[:max_pages]:  # Limit to 5 pages
                result["searched_urls"].append(check_url)
                result["pages_crawled"] += 1
                
                try:
                    if not is_safe_url(check_url):
                        continue
                    # Redirects are deliberately not followed: Location may target internal services.
                    with client.stream("GET", check_url, headers=headers) as response:
                        if response.status_code != 200:
                            continue
                        payload = bytearray()
                        for chunk in response.iter_bytes(chunk_size=65536):
                            payload.extend(chunk)
                            if len(payload) > 2_000_000:
                                break
                        if len(payload) > 2_000_000:
                            continue
                        text = payload.decode(response.encoding or "utf-8", errors="replace")
                    if text:
                        
                        # Extract emails
                        emails = extract_emails(text)
                        if emails:
                            result["email"] = emails[0]
                            result["evidence_url"] = check_url
                            
                            # Find snippet around email
                            email_pos = text.lower().find(emails[0].lower())
                            if email_pos >= 0:
                                start = max(0, email_pos - 100)
                                end = min(len(text), email_pos + 150)
                                snippet = text[start:end]
                                # Clean HTML
                                snippet = re.sub(r'<[^>]+>', ' ', snippet)
                                snippet = re.sub(r'\s+', ' ', snippet).strip()
                                result["evidence_snippet"] = snippet[:300]
                            
                            result["found"] = True
                        
                        # Extract phones if no email found
                        if not result["found"]:
                            phones = extract_phones(text)
                            if phones:
                                result["phone"] = phones[0]
                                result["evidence_url"] = check_url
                                result["found"] = True
                        
                        if result["found"]:
                            break
                
                except httpx.RequestError:
                    continue
    
    except Exception as e:
        logger.error(f"Contact finder error for {url}: {e}")
    
    return result


@router.post("/opportunities/{opportunity_id}/find", response_model=ContactFinderResponse)
def find_contact(
    opportunity_id: int,
    data: ContactFinderRequest = ContactFinderRequest(),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Find contact information for an opportunity.
    Uses official-first strategy with evidence requirement.
    """
    start_time = time.time()
    
    # Get opportunity
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id
    ).first()
    
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    
    # Check if contact already exists
    if opportunity.contact_email or opportunity.contact_phone:
        # Return existing contact info
        return ContactFinderResponse(
            id=0,  # Existing opportunity contact, no search-result row
            opportunity_id=opportunity_id,
            status="already_found",
            contact_email=opportunity.contact_email,
            contact_phone=opportunity.contact_phone,
            pages_crawled=0,
            created_at=datetime.utcnow(),
        )
    
    # Check for existing search result
    existing = db.query(ContactFinderResult).filter(
        ContactFinderResult.opportunity_id == opportunity_id
    ).first()
    
    if existing and existing.status == "found":
        return ContactFinderResponse.model_validate(existing)
    
    # Perform search
    allowed_domains = data.allowed_domains or DEFAULT_ALLOWED_DOMAINS
    
    search_result = search_official_website(
        opportunity.url_primary,
        allowed_domains, max_pages=data.max_pages
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Determine status
    if search_result["found"]:
        status_str = "found"
    else:
        status_str = "not_found"
    
    # Create or update result
    if existing:
        existing.status = status_str
        existing.contact_email = search_result.get("email")
        existing.contact_phone = search_result.get("phone")
        existing.contact_name = search_result.get("name")
        existing.evidence_url = search_result.get("evidence_url")
        existing.evidence_snippet = search_result.get("evidence_snippet")
        existing.searched_urls = search_result.get("searched_urls", [])
        existing.search_duration_ms = duration_ms
        existing.pages_crawled = search_result.get("pages_crawled", 0)
        existing.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing)
        result = existing
    else:
        result = ContactFinderResult(
            opportunity_id=opportunity_id,
            status=status_str,
            contact_email=search_result.get("email"),
            contact_phone=search_result.get("phone"),
            contact_name=search_result.get("name"),
            evidence_url=search_result.get("evidence_url"),
            evidence_snippet=search_result.get("evidence_snippet"),
            evidence_domain=search_result.get("evidence_url", "").split("/")[2] if search_result.get("evidence_url") else None,
            searched_urls=search_result.get("searched_urls", []),
            search_method="official_first" if data.search_official_first else "general",
            search_duration_ms=duration_ms,
            pages_crawled=search_result.get("pages_crawled", 0),
        )
        db.add(result)
        db.commit()
        db.refresh(result)
    
    # If found, update opportunity
    if status_str == "found":
        if search_result.get("email"):
            opportunity.contact_email = search_result["email"]
        if search_result.get("phone"):
            opportunity.contact_phone = search_result["phone"]
        if search_result.get("evidence_url"):
            opportunity.contact_url = search_result["evidence_url"]
        db.commit()
    
    return ContactFinderResponse(
        id=result.id,
        opportunity_id=result.opportunity_id,
        status=result.status,
        contact_email=result.contact_email,
        contact_phone=result.contact_phone,
        contact_name=result.contact_name,
        contact_role=result.contact_role,
        evidence_url=result.evidence_url,
        evidence_snippet=result.evidence_snippet,
        evidence_domain=result.evidence_domain,
        search_duration_ms=result.search_duration_ms,
        pages_crawled=result.pages_crawled,
        created_at=result.created_at,
    )


@router.get("/opportunities/{opportunity_id}/result", response_model=Optional[ContactFinderResponse])
def get_contact_finder_result(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get existing contact finder result for an opportunity"""
    result = db.query(ContactFinderResult).filter(
        ContactFinderResult.opportunity_id == opportunity_id
    ).first()
    
    if not result:
        return None
    
    return ContactFinderResponse.model_validate(result)


@router.get("/stats")
def get_contact_finder_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get contact finder statistics"""
    from sqlalchemy import func
    
    total = db.query(func.count(ContactFinderResult.id)).scalar()
    found = db.query(func.count(ContactFinderResult.id)).filter(
        ContactFinderResult.status == "found"
    ).scalar()
    not_found = db.query(func.count(ContactFinderResult.id)).filter(
        ContactFinderResult.status == "not_found"
    ).scalar()
    
    avg_duration = db.query(func.avg(ContactFinderResult.search_duration_ms)).filter(
        ContactFinderResult.search_duration_ms.isnot(None)
    ).scalar() or 0
    
    avg_pages = db.query(func.avg(ContactFinderResult.pages_crawled)).filter(
        ContactFinderResult.pages_crawled > 0
    ).scalar() or 0
    
    return {
        "total_searches": total,
        "found": found,
        "not_found": not_found,
        "success_rate": round(found / total * 100, 1) if total > 0 else 0,
        "avg_search_duration_ms": round(avg_duration),
        "avg_pages_crawled": round(avg_pages, 1),
    }
