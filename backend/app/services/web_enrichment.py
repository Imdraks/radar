"""
Web Enrichment Service - Actors for finding missing information.
Pipeline 3: Web lookup actors that GPT cannot do directly.

RULES:
- GPT does NOT browse - this service does
- Each actor searches for specific fields
- Results include source URL + evidence snippet
- Priority to official sources (gov, org sites)
- Rate limiting and robots.txt compliance
"""
import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.opportunity import Opportunity
from app.db.models.dossier import (
    SourceDocument, DocType,
    Dossier, DossierState,
    WebEnrichmentRun,
)

logger = logging.getLogger(__name__)


# Rate limiting per domain
_domain_last_request: Dict[str, float] = {}
MIN_REQUEST_INTERVAL = 2.0  # seconds between requests to same domain


class WebEnrichmentResult:
    """Result from a web lookup actor"""
    
    def __init__(
        self,
        field_key: str,
        value: Any,
        source_url: str,
        evidence_snippet: str,
        confidence: int = 50,
        method: str = "web_search"
    ):
        self.field_key = field_key
        self.value = value
        self.source_url = source_url
        self.evidence_snippet = evidence_snippet[:300]
        self.confidence = confidence
        self.method = method
        self.retrieved_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_key": self.field_key,
            "value": self.value,
            "source_url": self.source_url,
            "evidence_snippet": self.evidence_snippet,
            "confidence": self.confidence,
            "method": self.method,
            "retrieved_at": self.retrieved_at,
        }


class BaseWebActor:
    """Base class for web lookup actors"""
    
    def __init__(self):
        self.timeout = 30
        self.user_agent = getattr(settings, 'ingestion_user_agent', 
                                  'Mozilla/5.0 (compatible; OpportunityRadar/1.0)')
        self.max_retries = 2
    
    async def _rate_limit(self, url: str):
        """Apply rate limiting per domain"""
        domain = urlparse(url).netloc
        last_request = _domain_last_request.get(domain, 0)
        elapsed = time.time() - last_request
        
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
        
        _domain_last_request[domain] = time.time()
    
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with rate limiting"""
        await self._rate_limit(url)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    'User-Agent': self.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                }
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None
    
    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove scripts, styles, nav, footer
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        return soup.get_text(separator=' ', strip=True)
    
    def _is_official_source(self, url: str) -> bool:
        """Check if URL is from an official/trusted source"""
        domain = urlparse(url).netloc.lower()
        
        official_patterns = [
            '.gouv.fr', '.gov.', '.europa.eu',
            'marches-publics', 'achatpublic', 'boamp',
            'ted.europa', 'sam.gov',
        ]
        
        return any(pattern in domain for pattern in official_patterns)
    
    async def search(
        self,
        opportunity: Opportunity,
        urls_to_check: List[str]
    ) -> List[WebEnrichmentResult]:
        """
        Search for missing information.
        Must be implemented by subclasses.
        """
        raise NotImplementedError


class ContactLookupActor(BaseWebActor):
    """Actor for finding contact information (email, phone, URL)"""
    
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PHONE_PATTERN = re.compile(r'(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}')
    
    async def search(
        self,
        opportunity: Opportunity,
        urls_to_check: List[str]
    ) -> List[WebEnrichmentResult]:
        results = []
        
        for url in urls_to_check[:5]:  # Limit to 5 URLs
            html = await self._fetch_url(url)
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'lxml')
            text = self._extract_text(html)
            
            # Look for email
            if not opportunity.contact_email:
                emails = self.EMAIL_PATTERN.findall(text)
                # Filter out generic emails
                for email in emails:
                    if not any(x in email.lower() for x in ['noreply', 'no-reply', 'unsubscribe', 'newsletter']):
                        # Find context around email
                        idx = text.find(email)
                        snippet = text[max(0, idx-100):idx+len(email)+100].strip()
                        
                        confidence = 80 if self._is_official_source(url) else 60
                        
                        results.append(WebEnrichmentResult(
                            field_key="contact_email",
                            value=email,
                            source_url=url,
                            evidence_snippet=snippet,
                            confidence=confidence,
                            method="email_extraction"
                        ))
                        break
            
            # Look for phone
            if not opportunity.contact_phone:
                phones = self.PHONE_PATTERN.findall(text)
                for phone in phones:
                    idx = text.find(phone)
                    snippet = text[max(0, idx-100):idx+len(phone)+100].strip()
                    
                    confidence = 75 if self._is_official_source(url) else 55
                    
                    results.append(WebEnrichmentResult(
                        field_key="contact_phone",
                        value=phone.replace(' ', '').replace('.', '').replace('-', ''),
                        source_url=url,
                        evidence_snippet=snippet,
                        confidence=confidence,
                        method="phone_extraction"
                    ))
                    break
            
            # Look for contact page link
            if not opportunity.contact_url:
                contact_links = soup.find_all('a', href=True)
                for link in contact_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True).lower()
                    
                    if any(word in link_text or word in href.lower() 
                           for word in ['contact', 'nous-contacter', 'coordonnées']):
                        full_url = href if href.startswith('http') else urljoin(url, href)
                        
                        results.append(WebEnrichmentResult(
                            field_key="contact_url",
                            value=full_url,
                            source_url=url,
                            evidence_snippet=f"Lien contact trouvé: {link_text}",
                            confidence=70,
                            method="link_extraction"
                        ))
                        break
        
        return results


class DeadlineLookupActor(BaseWebActor):
    """Actor for finding deadline/date information"""
    
    DATE_PATTERNS = [
        # French formats
        (r'(?:date\s*limite|deadline|clôture|échéance)[^\d]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})', 90),
        (r'(?:avant\s*le|jusqu\'?au|au\s*plus\s*tard)[^\d]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})', 85),
        (r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\s*(?:date\s*limite|deadline)', 85),
        # ISO format
        (r'(?:deadline|date.*limite)[^\d]*(\d{4}-\d{2}-\d{2})', 90),
        # Written dates
        (r'(?:date\s*limite|deadline)[^\d]*(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})', 85),
    ]
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Try to parse various date formats to ISO"""
        from dateutil import parser as date_parser
        
        try:
            # Try French month names
            french_months = {
                'janvier': 'January', 'février': 'February', 'mars': 'March',
                'avril': 'April', 'mai': 'May', 'juin': 'June',
                'juillet': 'July', 'août': 'August', 'septembre': 'September',
                'octobre': 'October', 'novembre': 'November', 'décembre': 'December'
            }
            
            for fr, en in french_months.items():
                date_str = date_str.replace(fr, en)
            
            parsed = date_parser.parse(date_str, dayfirst=True)
            return parsed.strftime('%Y-%m-%d')
        except:
            return None
    
    async def search(
        self,
        opportunity: Opportunity,
        urls_to_check: List[str]
    ) -> List[WebEnrichmentResult]:
        results = []
        
        for url in urls_to_check[:5]:
            html = await self._fetch_url(url)
            if not html:
                continue
            
            text = self._extract_text(html)
            text_lower = text.lower()
            
            for pattern, base_confidence in self.DATE_PATTERNS:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                
                for match in matches:
                    date_str = match.group(1)
                    parsed_date = self._parse_date(date_str)
                    
                    if parsed_date:
                        # Get context
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        snippet = text[start:end].strip()
                        
                        confidence = base_confidence
                        if self._is_official_source(url):
                            confidence += 10
                        
                        results.append(WebEnrichmentResult(
                            field_key="deadline_at",
                            value=parsed_date,
                            source_url=url,
                            evidence_snippet=snippet,
                            confidence=min(confidence, 100),
                            method="date_pattern_extraction"
                        ))
                        return results  # Stop at first good match
        
        return results


class BudgetLookupActor(BaseWebActor):
    """Actor for finding budget/amount information"""
    
    BUDGET_PATTERNS = [
        # French formats
        (r'(?:budget|montant|enveloppe)[^\d€]*(\d[\d\s]*(?:\d{3}|\d))\s*€', 85),
        (r'(\d[\d\s]*(?:\d{3}|\d))\s*€\s*(?:HT|TTC|euros?)', 80),
        (r'(?:budget|montant)[^\d]*(\d+)\s*(?:000|k|K)\s*€?', 80),
        (r'entre\s*(\d[\d\s]*)\s*et\s*(\d[\d\s]*)\s*€', 75),  # Range
        # English formats
        (r'(?:budget|amount)[^\d€$]*[€$]\s*(\d[\d,]*)', 75),
    ]
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float"""
        try:
            # Remove spaces and thousand separators
            clean = amount_str.replace(' ', '').replace(',', '')
            
            # Handle 'k' suffix
            if 'k' in clean.lower():
                clean = clean.lower().replace('k', '')
                return float(clean) * 1000
            
            return float(clean)
        except:
            return None
    
    async def search(
        self,
        opportunity: Opportunity,
        urls_to_check: List[str]
    ) -> List[WebEnrichmentResult]:
        results = []
        
        for url in urls_to_check[:5]:
            html = await self._fetch_url(url)
            if not html:
                continue
            
            text = self._extract_text(html)
            text_lower = text.lower()
            
            for pattern, base_confidence in self.BUDGET_PATTERNS:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                
                for match in matches:
                    if len(match.groups()) == 2:
                        # Range pattern
                        min_amount = self._parse_amount(match.group(1))
                        max_amount = self._parse_amount(match.group(2))
                        if min_amount and max_amount:
                            # Get context
                            start = max(0, match.start() - 100)
                            end = min(len(text), match.end() + 100)
                            snippet = text[start:end].strip()
                            
                            confidence = base_confidence
                            if self._is_official_source(url):
                                confidence += 10
                            
                            # Add both amount and hint
                            results.append(WebEnrichmentResult(
                                field_key="budget_amount",
                                value=max_amount,
                                source_url=url,
                                evidence_snippet=snippet,
                                confidence=min(confidence, 100),
                                method="budget_pattern_extraction"
                            ))
                            results.append(WebEnrichmentResult(
                                field_key="budget_hint",
                                value=f"Entre {int(min_amount):,} et {int(max_amount):,} €".replace(',', ' '),
                                source_url=url,
                                evidence_snippet=snippet,
                                confidence=min(confidence, 100),
                                method="budget_pattern_extraction"
                            ))
                            return results
                    else:
                        # Single amount
                        amount = self._parse_amount(match.group(1))
                        if amount and amount >= 100:  # Ignore tiny amounts
                            start = max(0, match.start() - 100)
                            end = min(len(text), match.end() + 100)
                            snippet = text[start:end].strip()
                            
                            confidence = base_confidence
                            if self._is_official_source(url):
                                confidence += 10
                            
                            results.append(WebEnrichmentResult(
                                field_key="budget_amount",
                                value=amount,
                                source_url=url,
                                evidence_snippet=snippet,
                                confidence=min(confidence, 100),
                                method="budget_pattern_extraction"
                            ))
                            return results
        
        return results


class WebEnrichmentService:
    """
    Service orchestrating web enrichment actors.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.actors = {
            "contact": ContactLookupActor(),
            "deadline": DeadlineLookupActor(),
            "budget": BudgetLookupActor(),
        }
        
        # Map fields to actors
        self.field_actor_map = {
            "contact_email": "contact",
            "contact_phone": "contact",
            "contact_url": "contact",
            "deadline_at": "deadline",
            "budget_amount": "budget",
            "budget_hint": "budget",
        }
    
    def _get_urls_to_check(self, opportunity: Opportunity) -> List[str]:
        """Get list of URLs to check for the opportunity"""
        urls = []
        
        if opportunity.url_primary:
            urls.append(opportunity.url_primary)
        
        if opportunity.urls_all:
            urls.extend(opportunity.urls_all)
        
        # Deduplicate and limit
        seen = set()
        unique_urls = []
        for url in urls:
            if url and url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls[:10]
    
    async def enrich_dossier(
        self,
        dossier: Dossier,
        target_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run web enrichment for a dossier.
        
        Args:
            dossier: The dossier to enrich
            target_fields: Specific fields to look for (or use dossier.missing_fields)
        
        Returns:
            List of enrichment results
        """
        start_time = time.time()
        
        opportunity = dossier.opportunity
        
        # Determine which fields to look for
        fields_to_find = target_fields or dossier.missing_fields or []
        
        if not fields_to_find:
            logger.info(f"No fields to enrich for dossier {dossier.id}")
            return []
        
        # Create enrichment run record
        enrichment_run = WebEnrichmentRun(
            dossier_id=dossier.id,
            status="RUNNING",
            target_fields=fields_to_find,
            actors_used=[],
        )
        self.db.add(enrichment_run)
        
        # Update dossier state
        dossier.state = DossierState.ENRICHING
        self.db.commit()
        
        try:
            # Get URLs to check
            urls_to_check = self._get_urls_to_check(opportunity)
            enrichment_run.urls_consulted = urls_to_check
            
            # Determine which actors to use
            actors_to_run = set()
            for field in fields_to_find:
                actor_name = self.field_actor_map.get(field)
                if actor_name:
                    actors_to_run.add(actor_name)
            
            enrichment_run.actors_used = list(actors_to_run)
            
            # Run actors
            all_results: List[WebEnrichmentResult] = []
            errors = []
            
            for actor_name in actors_to_run:
                actor = self.actors.get(actor_name)
                if not actor:
                    continue
                
                try:
                    results = await actor.search(opportunity, urls_to_check)
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"Actor {actor_name} failed: {e}")
                    errors.append(f"{actor_name}: {str(e)[:200]}")
            
            # Store web documents
            for result in all_results:
                # Create source document for the web fetch
                existing = self.db.query(SourceDocument).filter(
                    SourceDocument.opportunity_id == opportunity.id,
                    SourceDocument.source_url == result.source_url,
                    SourceDocument.doc_type == DocType.WEB_EXTRACT
                ).first()
                
                if not existing:
                    source_doc = SourceDocument(
                        opportunity_id=opportunity.id,
                        doc_type=DocType.WEB_EXTRACT,
                        raw_text=result.evidence_snippet,
                        source_url=result.source_url,
                        fetched_at=datetime.utcnow(),
                        raw_metadata={
                            "field_key": result.field_key,
                            "value": result.value,
                            "method": result.method,
                            "confidence": result.confidence,
                        }
                    )
                    self.db.add(source_doc)
            
            # Update enrichment run
            fields_found = list(set(r.field_key for r in all_results))
            fields_not_found = [f for f in fields_to_find if f not in fields_found]
            
            enrichment_run.fields_found = fields_found
            enrichment_run.fields_not_found = fields_not_found
            enrichment_run.errors = errors
            enrichment_run.status = "SUCCESS" if not errors else "PARTIAL"
            enrichment_run.completed_at = datetime.utcnow()
            enrichment_run.duration_ms = int((time.time() - start_time) * 1000)
            
            self.db.commit()
            
            logger.info(f"Enrichment completed for dossier {dossier.id}. "
                       f"Found: {fields_found}, Missing: {fields_not_found}")
            
            return [r.to_dict() for r in all_results]
            
        except Exception as e:
            logger.error(f"Web enrichment failed for dossier {dossier.id}: {e}")
            enrichment_run.status = "FAILED"
            enrichment_run.errors = [str(e)[:500]]
            enrichment_run.completed_at = datetime.utcnow()
            enrichment_run.duration_ms = int((time.time() - start_time) * 1000)
            
            dossier.state = DossierState.FAILED
            dossier.last_error = f"Web enrichment failed: {str(e)[:500]}"
            
            self.db.commit()
            raise
    
    def run_enrichment_sync(
        self,
        dossier: Dossier,
        target_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for web enrichment.
        For use in Celery tasks.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.enrich_dossier(dossier, target_fields)
            )
        finally:
            loop.close()
