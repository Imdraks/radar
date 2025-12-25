"""
Dossier Builder Service - GPT-powered enrichment with grounded analysis.
Pipeline 2: Creates structured dossiers from source documents.

RULES:
- GPT only sees data from source_documents (grounded)
- GPT cannot browse the web
- Every extracted field MUST have evidence
- If field is missing after analysis -> flag it for web enrichment
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.opportunity import Opportunity
from app.db.models.dossier import (
    SourceDocument, DocType,
    Dossier, DossierState,
    DossierEvidence, EvidenceProvenance, EvidenceType,
)

logger = logging.getLogger(__name__)


# Critical fields that require evidence
CRITICAL_FIELDS = [
    "deadline_at", "budget_amount", "budget_hint",
    "contact_email", "contact_phone", "contact_url", "location"
]


class DossierBuilderService:
    """
    Service for building enriched dossiers using GPT.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = getattr(settings, 'openai_model', 'gpt-4o')
    
    def get_or_create_dossier(self, opportunity_id: UUID) -> Dossier:
        """Get existing dossier or create a new one"""
        dossier = self.db.query(Dossier).filter(
            Dossier.opportunity_id == opportunity_id
        ).first()
        
        if not dossier:
            dossier = Dossier(
                opportunity_id=opportunity_id,
                state=DossierState.NOT_CREATED
            )
            self.db.add(dossier)
            self.db.commit()
            self.db.refresh(dossier)
        
        return dossier
    
    def get_source_documents(self, opportunity_id: UUID) -> List[SourceDocument]:
        """Get all source documents for an opportunity"""
        return self.db.query(SourceDocument).filter(
            SourceDocument.opportunity_id == opportunity_id
        ).all()
    
    def build_gpt_context(
        self,
        opportunity: Opportunity,
        source_docs: List[SourceDocument]
    ) -> str:
        """
        Build the context string for GPT.
        Only includes actual collected data - no external browsing.
        """
        context_parts = []
        
        # Opportunity base info
        context_parts.append("=== OPPORTUNITÉ ===")
        context_parts.append(f"Titre: {opportunity.title}")
        context_parts.append(f"Source: {opportunity.source_name} ({opportunity.source_type.value})")
        context_parts.append(f"URL principale: {opportunity.url_primary or 'Non disponible'}")
        
        if opportunity.snippet:
            context_parts.append(f"Résumé existant: {opportunity.snippet}")
        if opportunity.organization:
            context_parts.append(f"Organisation: {opportunity.organization}")
        if opportunity.deadline_at:
            context_parts.append(f"Date limite (existante): {opportunity.deadline_at}")
        if opportunity.budget_amount:
            context_parts.append(f"Budget (existant): {opportunity.budget_amount} {opportunity.budget_currency}")
        if opportunity.contact_email:
            context_parts.append(f"Contact email (existant): {opportunity.contact_email}")
        
        # Source documents
        context_parts.append("\n=== DOCUMENTS SOURCES ===")
        
        for i, doc in enumerate(source_docs, 1):
            context_parts.append(f"\n--- Document {i} ({doc.doc_type.value}) ---")
            if doc.source_url:
                context_parts.append(f"URL: {doc.source_url}")
            
            # Include text content (truncated if too long)
            text = doc.raw_text or ""
            if len(text) > 8000:
                text = text[:8000] + "\n... [TRONQUÉ]"
            context_parts.append(f"Contenu:\n{text}")
        
        return "\n".join(context_parts)
    
    def build_gpt_prompt(self, context: str) -> str:
        """Build the structured prompt for GPT analysis"""
        return f"""Tu es un analyste expert en opportunités business. Analyse les documents fournis et crée un dossier structuré.

RÈGLES ABSOLUES:
1. Tu ne dois JAMAIS inventer d'informations
2. Chaque information extraite DOIT être présente dans les documents sources
3. Si une information n'est pas dans les documents, mets null
4. Fournis un snippet de preuve (evidence_snippet) pour chaque champ extrait (max 200 caractères)
5. Note ta confiance (0-100) pour chaque information extraite

{context}

Réponds UNIQUEMENT en JSON valide avec cette structure exacte:
{{
  "summary_short": "Résumé en 1-2 phrases (<500 caractères)",
  "summary_long": "Résumé détaillé en markdown (points clés, enjeux, opportunité)",
  "key_points": ["Point clé 1", "Point clé 2", "..."],
  "action_checklist": ["Action 1 à faire", "Action 2 à faire", "..."],
  "extracted_fields": {{
    "deadline_at": "2025-02-15" ou null,
    "budget_amount": 50000 ou null,
    "budget_hint": "texte indicatif budget" ou null,
    "location": {{"city": "Paris", "region": "IDF", "country": "FR"}} ou null,
    "contact_email": "email@example.fr" ou null,
    "contact_phone": "+33..." ou null,
    "contact_url": "https://..." ou null,
    "exigences": ["Exigence 1", "..."] ou [],
    "contraintes": ["Contrainte 1", "..."] ou [],
    "doc_list": ["document_mentionné.pdf", "..."] ou []
  }},
  "evidence": [
    {{
      "field_key": "deadline_at",
      "value": "2025-02-15",
      "evidence_snippet": "Date limite de dépôt : 15 février 2025",
      "confidence": 95,
      "source_index": 1
    }}
  ],
  "quality_flags": ["missing_budget", "missing_contact", ...] ou [],
  "confidence_plus": 75
}}

Les quality_flags possibles sont: missing_deadline, missing_budget, missing_contact, low_confidence, incomplete_requirements, unclear_scope.

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""
    
    def parse_gpt_response(self, response_text: str) -> Dict[str, Any]:
        """Parse GPT response, handling potential JSON issues"""
        # Try to extract JSON from response
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response: {e}")
            logger.error(f"Response was: {text[:500]}...")
            raise ValueError(f"Invalid JSON response from GPT: {e}")
    
    def create_evidence_records(
        self,
        dossier: Dossier,
        evidence_list: List[Dict[str, Any]],
        source_docs: List[SourceDocument]
    ) -> List[DossierEvidence]:
        """Create evidence records from GPT output"""
        evidence_records = []
        
        for ev in evidence_list:
            field_key = ev.get("field_key")
            if not field_key:
                continue
            
            # Determine source document
            source_doc = None
            source_idx = ev.get("source_index", 1) - 1
            if 0 <= source_idx < len(source_docs):
                source_doc = source_docs[source_idx]
            
            # Determine evidence type
            evidence_type = EvidenceType.HTML  # Default
            if source_doc:
                doc_type_map = {
                    DocType.EMAIL_HTML: EvidenceType.EMAIL,
                    DocType.EMAIL_TEXT: EvidenceType.EMAIL,
                    DocType.PDF_TEXT: EvidenceType.PDF,
                    DocType.WEB_SNAPSHOT_TEXT: EvidenceType.WEB,
                    DocType.WEB_EXTRACT: EvidenceType.WEB,
                }
                evidence_type = doc_type_map.get(source_doc.doc_type, EvidenceType.HTML)
            
            record = DossierEvidence(
                dossier_id=dossier.id,
                field_key=field_key,
                value=str(ev.get("value")) if ev.get("value") is not None else None,
                provenance=EvidenceProvenance.STANDARD_DOC,
                evidence_type=evidence_type,
                evidence_snippet=ev.get("evidence_snippet", "")[:500],
                confidence=ev.get("confidence", 50),
                source_document_id=source_doc.id if source_doc else None,
                source_url=source_doc.source_url if source_doc else None,
            )
            evidence_records.append(record)
            self.db.add(record)
        
        return evidence_records
    
    def identify_missing_fields(self, extracted_fields: Dict[str, Any]) -> List[str]:
        """Identify critical fields that are missing"""
        missing = []
        
        for field in CRITICAL_FIELDS:
            value = extracted_fields.get(field)
            
            # Handle nested location
            if field == "location":
                if not value or (isinstance(value, dict) and not value.get("city")):
                    missing.append(field)
            elif value is None or value == "":
                missing.append(field)
        
        return missing
    
    def build_dossier(
        self,
        opportunity_id: UUID,
        force_rebuild: bool = False
    ) -> Tuple[Dossier, bool]:
        """
        Build or update a dossier for an opportunity.
        
        Returns:
            (dossier, needs_web_enrichment)
        """
        start_time = time.time()
        
        # Get opportunity
        opportunity = self.db.query(Opportunity).filter(
            Opportunity.id == opportunity_id
        ).first()
        
        if not opportunity:
            raise ValueError(f"Opportunity not found: {opportunity_id}")
        
        # Get or create dossier
        dossier = self.get_or_create_dossier(opportunity_id)
        
        # Check if we should rebuild
        if not force_rebuild and dossier.state == DossierState.READY:
            logger.info(f"Dossier already ready for opportunity {opportunity_id}")
            return dossier, False
        
        # Update state
        dossier.state = DossierState.PROCESSING
        dossier.last_error = None
        self.db.commit()
        
        try:
            # Get source documents
            source_docs = self.get_source_documents(opportunity_id)
            
            if not source_docs:
                logger.warning(f"No source documents for opportunity {opportunity_id}")
                # Create a minimal dossier from opportunity data only
                dossier.summary_short = opportunity.snippet or opportunity.title
                dossier.quality_flags = ["no_source_documents"]
                dossier.missing_fields = CRITICAL_FIELDS.copy()
                dossier.state = DossierState.READY
                dossier.confidence_plus = 20
                dossier.processed_at = datetime.utcnow()
                self.db.commit()
                return dossier, True
            
            # Build context and prompt
            context = self.build_gpt_context(opportunity, source_docs)
            prompt = self.build_gpt_prompt(context)
            
            # Call GPT
            logger.info(f"Calling GPT for dossier analysis of opportunity {opportunity_id}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un analyste expert. Réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            
            # Track usage
            tokens_used = response.usage.total_tokens if response.usage else 0
            dossier.tokens_used = tokens_used
            dossier.gpt_model_used = self.model
            
            # Parse response
            response_text = response.choices[0].message.content
            parsed = self.parse_gpt_response(response_text)
            
            # Update dossier
            dossier.summary_short = parsed.get("summary_short", "")[:500]
            dossier.summary_long = parsed.get("summary_long", "")
            dossier.key_points = parsed.get("key_points", [])
            dossier.action_checklist = parsed.get("action_checklist", [])
            dossier.extracted_fields = parsed.get("extracted_fields", {})
            dossier.confidence_plus = parsed.get("confidence_plus", 50)
            dossier.quality_flags = parsed.get("quality_flags", [])
            
            # Track source documents used
            dossier.sources_used = [str(doc.id) for doc in source_docs]
            
            # Create evidence records
            existing_evidence = self.db.query(DossierEvidence).filter(
                DossierEvidence.dossier_id == dossier.id,
                DossierEvidence.provenance == EvidenceProvenance.STANDARD_DOC
            ).all()
            for ev in existing_evidence:
                self.db.delete(ev)
            
            evidence_list = parsed.get("evidence", [])
            self.create_evidence_records(dossier, evidence_list, source_docs)
            
            # Identify missing fields
            extracted = parsed.get("extracted_fields", {})
            missing = self.identify_missing_fields(extracted)
            dossier.missing_fields = missing
            
            # Add missing field flags if not already present
            for field in missing:
                flag = f"missing_{field.replace('_at', '').replace('_', '')}"
                if flag not in dossier.quality_flags:
                    dossier.quality_flags.append(flag)
            
            # Calculate final score
            base_score = opportunity.score_base if hasattr(opportunity, 'score_base') else opportunity.score
            dossier.calculate_final_score(base_score or 0)
            
            # Mark as ready
            dossier.state = DossierState.READY
            dossier.processed_at = datetime.utcnow()
            dossier.processing_time_ms = int((time.time() - start_time) * 1000)
            
            self.db.commit()
            
            needs_enrichment = len(missing) > 0
            logger.info(f"Dossier built for opportunity {opportunity_id}. "
                       f"Missing fields: {missing}. Needs enrichment: {needs_enrichment}")
            
            return dossier, needs_enrichment
            
        except Exception as e:
            logger.error(f"Error building dossier for opportunity {opportunity_id}: {e}")
            dossier.state = DossierState.FAILED
            dossier.last_error = str(e)[:1000]
            dossier.retry_count += 1
            dossier.processing_time_ms = int((time.time() - start_time) * 1000)
            self.db.commit()
            raise
    
    def merge_after_enrichment(
        self,
        dossier_id: UUID,
        enrichment_results: List[Dict[str, Any]]
    ) -> Dossier:
        """
        Merge web enrichment results into the dossier.
        Re-run GPT with enriched data for final analysis.
        """
        dossier = self.db.query(Dossier).filter(Dossier.id == dossier_id).first()
        if not dossier:
            raise ValueError(f"Dossier not found: {dossier_id}")
        
        opportunity = dossier.opportunity
        
        dossier.state = DossierState.MERGING
        self.db.commit()
        
        try:
            # Get original source documents
            original_docs = self.get_source_documents(opportunity.id)
            
            # Get newly added web enrichment documents
            web_docs = self.db.query(SourceDocument).filter(
                SourceDocument.opportunity_id == opportunity.id,
                SourceDocument.doc_type.in_([DocType.WEB_SNAPSHOT_TEXT, DocType.WEB_EXTRACT])
            ).all()
            
            # Build context with all documents
            all_docs = original_docs + web_docs
            context = self.build_gpt_context(opportunity, all_docs)
            
            # Add enrichment context
            enrichment_context = "\n\n=== RÉSULTATS ENRICHISSEMENT WEB ===\n"
            for result in enrichment_results:
                enrichment_context += f"\nChamp: {result['field_key']}\n"
                enrichment_context += f"Valeur trouvée: {result['value']}\n"
                enrichment_context += f"Source: {result['source_url']}\n"
                enrichment_context += f"Extrait: {result['evidence_snippet']}\n"
            
            full_context = context + enrichment_context
            prompt = self.build_gpt_prompt(full_context)
            
            # Call GPT for merge
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un analyste expert. Intègre les nouvelles données web dans ton analyse. Réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            
            dossier.tokens_used += response.usage.total_tokens if response.usage else 0
            
            # Parse and update
            response_text = response.choices[0].message.content
            parsed = self.parse_gpt_response(response_text)
            
            # Update dossier with merged data
            dossier.summary_short = parsed.get("summary_short", dossier.summary_short)[:500]
            dossier.summary_long = parsed.get("summary_long", dossier.summary_long)
            dossier.key_points = parsed.get("key_points", dossier.key_points)
            dossier.action_checklist = parsed.get("action_checklist", dossier.action_checklist)
            dossier.extracted_fields = parsed.get("extracted_fields", dossier.extracted_fields)
            dossier.confidence_plus = parsed.get("confidence_plus", dossier.confidence_plus)
            
            # Update quality flags
            new_flags = parsed.get("quality_flags", [])
            dossier.quality_flags = new_flags
            
            # Add evidence from enrichment
            for result in enrichment_results:
                evidence = DossierEvidence(
                    dossier_id=dossier.id,
                    field_key=result['field_key'],
                    value=str(result['value']),
                    provenance=EvidenceProvenance.WEB_ENRICHED,
                    evidence_type=EvidenceType.WEB,
                    evidence_ref=result['source_url'],
                    evidence_snippet=result['evidence_snippet'][:500],
                    confidence=result.get('confidence', 70),
                    source_url=result['source_url'],
                    retrieved_at=datetime.fromisoformat(result['retrieved_at']) if result.get('retrieved_at') else datetime.utcnow(),
                    retrieval_method=result.get('method', 'web_search'),
                )
                self.db.add(evidence)
            
            # Re-identify missing fields
            extracted = parsed.get("extracted_fields", {})
            missing = self.identify_missing_fields(extracted)
            dossier.missing_fields = missing
            
            # Recalculate score
            base_score = opportunity.score_base if hasattr(opportunity, 'score_base') else opportunity.score
            dossier.calculate_final_score(base_score or 0)
            
            dossier.state = DossierState.READY
            dossier.enriched_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Dossier merged with enrichment results. "
                       f"Still missing: {missing}")
            
            return dossier
            
        except Exception as e:
            logger.error(f"Error merging dossier {dossier_id}: {e}")
            dossier.state = DossierState.FAILED
            dossier.last_error = str(e)[:1000]
            self.db.commit()
            raise
