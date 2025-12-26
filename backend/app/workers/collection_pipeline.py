"""
Collection Pipeline - Celery Tasks

Pipeline Standard: Sources → Fetch → Extract → LeadItems → Dedup → Score
Pipeline IA (3 phases): Plan GPT → Fetch URLs → Dossier Builder

Tous les résultats sont sourcés avec Evidence (zéro hallucination).
"""
import hashlib
import time
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from celery import shared_task, chain, group
from sqlalchemy.orm import Session
from sqlalchemy import func
import openai

from app.db.session import SessionLocal
from app.db.models.collections import (
    CollectionV2, CollectionLog, LeadItem, CollectionResult,
    SourceDocumentV2, DossierV2, Evidence,
    CollectionType, CollectionStatus, LeadItemKind, LeadItemStatus,
    DossierState, EvidenceProvenance
)
from app.db.models.source import SourceConfig
from app.core.config import settings
from app.workers.task_logger import TaskLogger, get_task_logger, Colors


# ================================================================
# PIPELINE STANDARD: Sources → Fetch → Extract → Score → Dedup
# ================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_standard_collection(self, collection_id: str):
    """
    Lance une collecte Standard.
    
    Flow:
    1. Load sources from DB
    2. Pour chaque source: fetch → parse → extract items
    3. Deduplication via canonical_hash
    4. Scoring
    5. Insertion dans lead_items + collection_results
    """
    log = get_task_logger("pipeline", collection_id=collection_id)
    log.step(f"Collecte STANDARD démarrée")
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        collection = db.query(CollectionV2).filter(
            CollectionV2.id == collection_id
        ).first()
        
        if not collection:
            log.error(f"Collection {collection_id} not found")
            return {"error": "Collection not found"}
        
        # Update status
        collection.status = CollectionStatus.RUNNING.value
        collection.started_at = datetime.utcnow()
        db.commit()
        
        _log(db, collection_id, "info", "Démarrage collecte Standard")
        
        # 1. Charger les sources depuis les params
        params = collection.params or {}
        source_ids = params.get("source_ids") or []
        if not source_ids:
            # Toutes les sources actives
            sources = db.query(SourceConfig).filter(SourceConfig.is_active == True).all()
        else:
            sources = db.query(SourceConfig).filter(SourceConfig.id.in_(source_ids)).all()
        
        log.info(f"Sources chargées: {len(sources)}", save=True)
        
        total_extracted = 0
        total_new = 0
        total_duplicates = 0
        errors = []
        
        # 2. Pour chaque source
        for idx, source in enumerate(sources, 1):
            source_log = get_task_logger("http", collection_id=collection_id)
            print(f"{Colors.CYAN}   [{idx}/{len(sources)}] Source: {source.name} ({source.connector_type}){Colors.RESET}", flush=True)
            
            try:
                with log.timer(f"Source {source.name}"):
                    items_from_source = _process_source(db, collection_id, source, log)
                
                # 3. Dedup + Insert
                for item_data in items_from_source:
                    is_new, lead_item = _dedup_and_insert(
                        db, collection_id, source, item_data
                    )
                    total_extracted += 1
                    if is_new:
                        total_new += 1
                    else:
                        total_duplicates += 1
                
                print(f"{Colors.GREEN}      ✓ {source.name}: {len(items_from_source)} items ({total_new} nouveaux){Colors.RESET}", flush=True)
                _log(db, collection_id, "info", 
                     f"Source {source.name}: {len(items_from_source)} items")
                
            except Exception as e:
                source_log.exception(f"Error processing source {source.name}")
                errors.append(f"{source.name}: {str(e)}")
                print(f"{Colors.RED}      ✗ {source.name}: {e}{Colors.RESET}", flush=True)
                _log(db, collection_id, "error", 
                     f"Erreur source {source.name}: {str(e)}")
        
        # 4. Mise à jour finale
        elapsed = int((time.time() - start_time) * 1000)
        
        # Count results
        result_count = db.query(func.count(CollectionResult.id)).filter(
            CollectionResult.collection_id == collection_id
        ).scalar()
        
        collection.status = CollectionStatus.DONE.value
        collection.finished_at = datetime.utcnow()
        collection.stats = {
            "sources_processed": len(sources),
            "items_extracted": total_extracted,
            "items_new": total_new,
            "items_duplicate": total_duplicates,
            "result_count": result_count,
            "errors": errors,
            "processing_time_ms": elapsed,
        }
        
        db.commit()
        
        log.success(f"Collecte terminée en {log.elapsed_str()}", 
                   new=total_new, duplicates=total_duplicates, save=True)
        
        return {
            "status": "success",
            "items_new": total_new,
            "items_duplicate": total_duplicates,
            "processing_time_ms": elapsed,
        }
        
    except Exception as e:
        log.error(f"Collection {collection_id} failed: {e}", save=True)
        if collection:
            collection.status = CollectionStatus.ERROR.value
            collection.error_message = str(e)
            db.commit()
        _log(db, collection_id, "error", f"Erreur fatale: {str(e)}")
        raise self.retry(exc=e)
        
    finally:
        db.close()


def _process_source(db: Session, collection_id: str, source: SourceConfig, log: TaskLogger = None) -> List[Dict]:
    """
    Fetch + Parse + Extract items from a source.
    Retourne liste de dicts avec les données extraites.
    """
    from app.ingestion.factory import create_connector
    from app.extraction.extraction_service import ExtractionService
    
    if log is None:
        log = get_task_logger("crawler")
    
    items = []
    
    try:
        # Create connector based on source type
        connector = create_connector(source)
        log.debug(f"Connecteur créé: {type(connector).__name__}")
        
        # Fetch raw content
        raw_content = connector.fetch()
        log.debug(f"Contenu récupéré: {len(raw_content) if raw_content else 0} chars")
        
        # Store as SourceDocumentV2
        doc = SourceDocumentV2(
            url=source.url,
            source_id=source.id,
            raw_html=raw_content[:50000] if raw_content else None,  # Limit size
            fetched_at=datetime.utcnow(),
        )
        db.add(doc)
        db.flush()
        
        # Extract structured items
        extractor = ExtractionService()
        extracted_items = extractor.extract_opportunities(
            raw_content, 
            source_name=source.name,
            source_type=source.source_type,
        )
        
        log.info(f"Extraction: {len(extracted_items)} items de {source.name}")
        
        for item in extracted_items:
            item["source_document_id"] = str(doc.id)
            item["source_id"] = source.id
            item["source_name"] = source.name
            item["source_type"] = source.source_type
            items.append(item)
        
    except Exception as e:
        log.warning(f"Échec source {source.name}: {e}")
        raise
    
    return items


def _dedup_and_insert(
    db: Session, 
    collection_id: str, 
    source: SourceConfig, 
    item_data: Dict
) -> tuple[bool, LeadItem]:
    """
    Déduplique via canonical_hash et insère si nouveau.
    Retourne (is_new, lead_item).
    """
    # Compute canonical hash
    canonical_hash = _compute_canonical_hash(item_data)
    
    # Check if exists
    existing = db.query(LeadItem).filter(
        LeadItem.canonical_hash == canonical_hash
    ).first()
    
    if existing:
        # Just link to collection result
        _link_to_collection(db, collection_id, existing.id)
        return False, existing
    
    # Also check by URL
    if item_data.get("url_primary"):
        existing_by_url = db.query(LeadItem).filter(
            LeadItem.url_primary == item_data["url_primary"]
        ).first()
        if existing_by_url:
            _link_to_collection(db, collection_id, existing_by_url.id)
            return False, existing_by_url
    
    # Score the item
    from app.scoring.base_scorer import BaseScorer
    scorer = BaseScorer()
    score_result = scorer.score(item_data)
    
    # Create new LeadItem
    lead_item = LeadItem(
        kind=LeadItemKind.OPPORTUNITY.value,
        canonical_hash=canonical_hash,
        title=item_data.get("title", "Sans titre")[:500],
        description=item_data.get("description", "")[:5000],
        organization_name=item_data.get("organization_name"),
        url_primary=item_data.get("url_primary"),
        source_name=source.name,
        source_type=source.source_type,
        source_id=source.id,
        published_at=_parse_date(item_data.get("published_at")),
        deadline_at=_parse_date(item_data.get("deadline_at")),
        location_city=item_data.get("location_city"),
        location_region=item_data.get("location_region"),
        budget_min=item_data.get("budget_min"),
        budget_max=item_data.get("budget_max"),
        budget_display=item_data.get("budget_display"),
        contact_email=item_data.get("contact_email"),
        contact_phone=item_data.get("contact_phone"),
        contact_url=item_data.get("contact_url"),
        contact_name=item_data.get("contact_name"),
        has_contact=bool(
            item_data.get("contact_email") or 
            item_data.get("contact_phone") or 
            item_data.get("contact_url")
        ),
        has_deadline=bool(item_data.get("deadline_at")),
        score_base=score_result.get("score", 50),
        score_breakdown=score_result.get("breakdown"),
        status=LeadItemStatus.NEW.value,
        metadata=item_data.get("metadata"),
    )
    db.add(lead_item)
    db.flush()
    
    # Link to collection
    _link_to_collection(db, collection_id, lead_item.id)
    
    db.commit()
    return True, lead_item


def _link_to_collection(db: Session, collection_id: str, lead_item_id: UUID):
    """Link a lead_item to a collection via collection_results"""
    existing = db.query(CollectionResult).filter(
        CollectionResult.collection_id == collection_id,
        CollectionResult.lead_item_id == lead_item_id
    ).first()
    
    if not existing:
        result = CollectionResult(
            collection_id=collection_id,
            lead_item_id=lead_item_id,
        )
        db.add(result)


def _compute_canonical_hash(item_data: Dict) -> str:
    """
    Compute canonical hash for deduplication.
    Based on: normalized title + organization + url_primary
    """
    title = (item_data.get("title") or "").lower().strip()
    org = (item_data.get("organization_name") or "").lower().strip()
    url = (item_data.get("url_primary") or "").lower().strip()
    
    canonical_string = f"{title}|{org}|{url}"
    return hashlib.sha256(canonical_string.encode()).hexdigest()[:32]


# ================================================================
# PIPELINE IA: Plan → Fetch → Dossier Builder
# ================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def run_ai_collection(self, collection_id: str):
    """
    Lance une collecte IA (ChatGPT).
    
    Flow en 3 phases:
    Phase A: GPT génère un plan de recherche
    Phase B: Fetch les URLs du plan
    Phase C: GPT construit le dossier avec evidence
    """
    log = get_task_logger("gpt", collection_id=collection_id)
    log.step("Collecte IA démarrée")
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        collection = db.query(CollectionV2).filter(
            CollectionV2.id == collection_id
        ).first()
        
        if not collection:
            return {"error": "Collection not found"}
        
        collection.status = CollectionStatus.RUNNING.value
        collection.started_at = datetime.utcnow()
        db.commit()
        
        _log(db, collection_id, "info", "Démarrage collecte IA")
        
        # Get parameters
        params = collection.parameters or {}
        query = params.get("query", "")
        objective = params.get("objective", "PROSPECTION")
        target_entities = params.get("target_entities", [])
        
        if not query:
            raise ValueError("Query is required for AI collection")
        
        log.info(f"Query: {query[:80]}...", objective=objective)
        
        # Phase A: GPT Plan
        log.step("Phase A: Génération du plan GPT")
        _log(db, collection_id, "info", "Phase A: Génération du plan GPT")
        
        with log.timer("GPT Plan Generation"):
            plan = _gpt_generate_plan(query, objective, target_entities)
        
        log.info(f"Plan généré: {len(plan.get('urls', []))} URLs à fetcher")
        
        # Create lead_item for this search
        lead_item = LeadItem(
            kind=LeadItemKind.DOSSIER_CANDIDATE.value,
            title=f"Recherche IA: {query[:100]}",
            description=query,
            source_name="ai_search",
            source_type="ai",
            status=LeadItemStatus.NEW.value,
        )
        db.add(lead_item)
        db.flush()
        
        # Create dossier
        dossier = DossierV2(
            lead_item_id=lead_item.id,
            objective=objective,
            target_entities=[{"name": e, "type": "ORGANIZATION"} for e in target_entities],
            state=DossierState.PROCESSING.value,
        )
        db.add(dossier)
        db.flush()
        
        _link_to_collection(db, collection_id, lead_item.id)
        
        # Phase B: Fetch URLs from plan
        log.step(f"Phase B: Fetch {len(plan.get('urls', []))} URLs")
        _log(db, collection_id, "info", f"Phase B: Fetch {len(plan.get('urls', []))} URLs")
        
        with log.timer("URL Fetching"):
            fetched_docs = _fetch_plan_urls(db, dossier.id, lead_item.id, plan.get("urls", []), log)
        
        log.info(f"Documents récupérés: {len(fetched_docs)}")
        
        # Phase C: GPT Dossier Builder
        log.step("Phase C: Construction du dossier GPT")
        _log(db, collection_id, "info", "Phase C: Construction du dossier GPT")
        
        with log.timer("GPT Dossier Building"):
            dossier_result = _gpt_build_dossier(
                query, objective, target_entities, fetched_docs, plan, log
            )
        
        # Update dossier
        dossier.sections = dossier_result.get("sections")
        dossier.summary = dossier_result.get("summary")
        dossier.key_findings = dossier_result.get("key_findings")
        dossier.recommendations = dossier_result.get("recommendations")
        dossier.quality_score = dossier_result.get("quality_score", 0)
        dossier.quality_breakdown = dossier_result.get("quality_breakdown")
        dossier.tokens_used = dossier_result.get("tokens_used")
        dossier.model_used = dossier_result.get("model_used", "gpt-4")
        dossier.state = DossierState.READY.value
        
        log.info(f"Dossier construit: {len(dossier_result.get('sections', []))} sections")
        
        # Store evidence
        evidence_count = 0
        for ev in dossier_result.get("evidence", []):
            evidence = Evidence(
                dossier_id=dossier.id,
                lead_item_id=lead_item.id,
                source_document_id=ev.get("source_document_id"),
                field_name=ev.get("field_name"),
                value=ev.get("value"),
                quote=ev.get("quote"),
                url=ev.get("url"),
                provenance=ev.get("provenance", EvidenceProvenance.GPT_GROUNDED.value),
                confidence=ev.get("confidence", 0.8),
            )
            db.add(evidence)
            evidence_count += 1
        
        log.info(f"Evidence stocké: {evidence_count} éléments")
        
        # Finalize collection
        elapsed = int((time.time() - start_time) * 1000)
        collection.status = CollectionStatus.DONE.value
        collection.finished_at = datetime.utcnow()
        collection.stats = {
            "urls_fetched": len(fetched_docs),
            "evidence_count": len(dossier_result.get("evidence", [])),
            "quality_score": dossier_result.get("quality_score"),
            "tokens_used": dossier_result.get("tokens_used"),
            "result_count": 1,
            "processing_time_ms": elapsed,
        }
        
        db.commit()
        
        log.success(f"Collecte IA terminée en {log.elapsed_str()}", 
                   quality=dossier.quality_score,
                   tokens=dossier_result.get("tokens_used"),
                   save=True)
        
        _log(db, collection_id, "info", 
             f"Collecte IA terminée: score qualité {dossier.quality_score}")
        
        return {
            "status": "success",
            "dossier_id": str(dossier.id),
            "quality_score": dossier.quality_score,
        }
        
    except Exception as e:
        log.error(f"AI Collection failed: {e}", save=True)
        if collection:
            collection.status = CollectionStatus.ERROR.value
            collection.error_message = str(e)
            db.commit()
        _log(db, collection_id, "error", f"Erreur: {str(e)}")
        raise self.retry(exc=e)
        
    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def run_dossier_builder_task(self, dossier_id: str):
    """
    Construit/régénère un dossier existant.
    Appelé depuis opportunities_api.create_dossier_from_opportunity
    """
    log = get_task_logger("dossier")
    log.step(f"Construction dossier {dossier_id[:8]}")
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        dossier = db.query(DossierV2).filter(
            DossierV2.id == dossier_id
        ).first()
        
        if not dossier:
            log.error("Dossier not found", dossier_id=dossier_id)
            return {"error": "Dossier not found"}
        
        dossier.state = DossierState.PROCESSING.value
        db.commit()
        
        # Get lead_item
        lead_item = db.query(LeadItem).filter(
            LeadItem.id == dossier.lead_item_id
        ).first()
        
        if not lead_item:
            raise ValueError("Lead item not found")
        
        log.info(f"Dossier pour: {lead_item.title[:50]}...")
        
        # Build context from lead_item
        objective = dossier.objective
        target_entities = [e.get("name") for e in (dossier.target_entities or [])]
        
        # Phase A: Generate plan based on lead_item
        log.step("Phase A: Génération plan GPT")
        with log.timer("GPT Plan"):
            plan = _gpt_generate_plan(
                lead_item.title,
                objective,
                target_entities or [lead_item.organization_name],
            )
        
        # Phase B: Fetch URLs
        log.step(f"Phase B: Fetch {len(plan.get('urls', []))} URLs")
        with log.timer("URL Fetching"):
            fetched_docs = _fetch_plan_urls(
                db, dossier.id, lead_item.id, plan.get("urls", []), log
            )
        
        # Add lead_item URL to docs
        if lead_item.url_primary:
            log.debug(f"Fetch URL primaire: {lead_item.url_primary}")
            primary_doc = _fetch_single_url(db, dossier.id, lead_item.id, lead_item.url_primary)
            if primary_doc:
                fetched_docs.insert(0, primary_doc)
        
        log.info(f"Documents récupérés: {len(fetched_docs)}")
        
        # Phase C: Build dossier
        log.step("Phase C: Construction dossier GPT")
        with log.timer("GPT Dossier Building"):
            result = _gpt_build_dossier(
                lead_item.title,
                objective,
                target_entities,
                fetched_docs,
                plan,
                log,
            )
        
        # Update dossier
        dossier.sections = result.get("sections")
        dossier.summary = result.get("summary")
        dossier.key_findings = result.get("key_findings")
        dossier.recommendations = result.get("recommendations")
        dossier.quality_score = result.get("quality_score", 0)
        dossier.quality_breakdown = result.get("quality_breakdown")
        dossier.tokens_used = result.get("tokens_used")
        dossier.model_used = result.get("model_used", "gpt-4")
        dossier.processing_time_ms = int((time.time() - start_time) * 1000)
        dossier.state = DossierState.READY.value
        
        # Store evidence
        evidence_count = 0
        for ev in result.get("evidence", []):
            evidence = Evidence(
                dossier_id=dossier.id,
                lead_item_id=lead_item.id,
                source_document_id=ev.get("source_document_id"),
                field_name=ev.get("field_name"),
                value=ev.get("value"),
                quote=ev.get("quote"),
                url=ev.get("url"),
                provenance=ev.get("provenance", EvidenceProvenance.GPT_GROUNDED.value),
                confidence=ev.get("confidence", 0.8),
            )
            db.add(evidence)
            evidence_count += 1
        
        db.commit()
        
        log.success(f"Dossier prêt en {log.elapsed_str()}", 
                   quality=dossier.quality_score,
                   evidence=evidence_count)
        
        return {
            "status": "success",
            "quality_score": dossier.quality_score,
        }
        
    except Exception as e:
        log.error(f"Dossier builder failed: {e}")
        if dossier:
            dossier.state = DossierState.ERROR.value
            dossier.error_message = str(e)
            db.commit()
        raise self.retry(exc=e)
        
    finally:
        db.close()


# ================================================================
# GPT FUNCTIONS - OpenAI Integration
# ================================================================

def _get_openai_client():
    """Initialize OpenAI client"""
    api_key = getattr(settings, 'openai_api_key', None) or settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")
    return openai.OpenAI(api_key=api_key)


def _gpt_generate_plan(query: str, objective: str, target_entities: List[str]) -> Dict:
    """
    Phase A: GPT génère un plan de recherche.
    Retourne: { urls: [...], search_queries: [...], strategy: str, rationale: str }
    """
    log = get_task_logger("gpt")
    try:
        client = _get_openai_client()
        
        entities_str = ", ".join(target_entities) if target_entities else "non spécifié"
        log.debug(f"Génération plan pour: {query[:50]}...", entities=len(target_entities))
        
        system_prompt = """Tu es un expert en recherche business et veille stratégique.
Ton rôle est de créer un plan de recherche pour trouver des informations sur une cible.

Tu dois retourner un JSON avec:
- urls: liste de 5-10 URLs pertinentes à consulter (sites officiels, LinkedIn, articles, etc.)
- search_queries: liste de 3-5 requêtes Google optimisées
- strategy: la stratégie de recherche (ex: "focus_company", "industry_scan", "decision_makers")
- rationale: explication courte du plan

Réponds UNIQUEMENT avec du JSON valide, sans texte avant ou après."""

        user_prompt = f"""Crée un plan de recherche pour:

Requête: {query}
Objectif: {objective}
Entités cibles: {entities_str}

Génère des URLs et requêtes pertinentes pour la France."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        
        content = response.choices[0].message.content.strip()
        log.info(f"GPT Plan reçu: {response.usage.total_tokens} tokens")
        
        # Parse JSON
        try:
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            
            plan = json.loads(content)
            plan["tokens_used"] = response.usage.total_tokens
            log.debug(f"Plan parsed: {len(plan.get('urls', []))} URLs")
            return plan
        except json.JSONDecodeError:
            log.warning(f"Échec parsing plan GPT")
            return {
                "urls": [],
                "search_queries": [query],
                "strategy": "fallback",
                "rationale": "Plan parsing failed, using direct search",
            }
            
    except Exception as e:
        log.error(f"GPT plan generation failed: {e}")
        return {
            "urls": [],
            "search_queries": [query],
            "strategy": "error_fallback",
            "rationale": f"Error: {str(e)}",
        }


def _gpt_build_dossier(
    query: str,
    objective: str,
    target_entities: List[str],
    documents: List[Dict],
    plan: Dict,
    log: TaskLogger = None,
) -> Dict:
    """
    Phase C: GPT construit le dossier avec evidence sourcée.
    
    IMPORTANT: Chaque affirmation doit être liée à une evidence avec:
    - quote: extrait exact du document source
    - url: URL du document
    - source_document_id: ID du document en DB
    """
    if log is None:
        log = get_task_logger("gpt")
    
    try:
        client = _get_openai_client()
        
        # Préparer le contexte des documents
        docs_context = []
        for i, doc in enumerate(documents[:5]):  # Limit to 5 docs
            content = doc.get("content", "")[:8000]  # Limit content
            docs_context.append(f"""
=== DOCUMENT {i+1} ===
URL: {doc.get('url', 'N/A')}
ID: {doc.get('id', 'N/A')}
CONTENU:
{content}
""")
        
        log.debug(f"Building dossier avec {len(docs_context)} documents")
        
        docs_text = "\n".join(docs_context) if docs_context else "Aucun document disponible."
        entities_str = ", ".join(target_entities) if target_entities else "non spécifié"
        
        system_prompt = """Tu es un expert en intelligence business. Tu crées des dossiers de prospection.

RÈGLE CRITIQUE: Tu ne dois JAMAIS inventer d'information. Chaque fait doit être extrait des documents fournis.

Tu dois retourner un JSON avec:
{
  "sections": [
    {
      "title": "Titre de section",
      "content": "Contenu de la section",
      "evidence_refs": ["DOC_ID:quote exacte"]
    }
  ],
  "summary": "Résumé exécutif (2-3 phrases)",
  "key_findings": ["Finding 1", "Finding 2", ...],
  "recommendations": ["Action 1", "Action 2", ...],
  "quality_score": 0-100,
  "quality_breakdown": {
    "completeness": 0-100,
    "source_quality": 0-100,
    "relevance": 0-100
  },
  "evidence": [
    {
      "field_name": "nom du champ",
      "value": "valeur extraite",
      "quote": "citation exacte du document",
      "url": "URL source",
      "source_document_id": "ID du document",
      "confidence": 0.0-1.0
    }
  ]
}

Réponds UNIQUEMENT avec du JSON valide."""

        user_prompt = f"""Crée un dossier de prospection:

REQUÊTE: {query}
OBJECTIF: {objective}
CIBLES: {entities_str}

DOCUMENTS SOURCES:
{docs_text}

Analyse ces documents et crée un dossier structuré. 
Chaque information doit avoir une evidence avec la citation exacte du document source."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        
        content = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens
        log.info(f"GPT Dossier reçu: {tokens_used} tokens")
        
        # Parse JSON
        try:
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            
            result = json.loads(content)
            result["tokens_used"] = tokens_used
            result["model_used"] = "gpt-4o"
            
            log.debug(f"Dossier parsed: {len(result.get('sections', []))} sections, {len(result.get('evidence', []))} evidence")
            
            # Validate evidence provenance
            for ev in result.get("evidence", []):
                ev["provenance"] = EvidenceProvenance.GPT_GROUNDED.value
                if "confidence" not in ev:
                    ev["confidence"] = 0.8
            
            return result
            
        except json.JSONDecodeError:
            log.warning(f"Échec parsing dossier GPT")
            return _fallback_dossier(query, tokens_used)
            
    except Exception as e:
        log.error(f"GPT dossier building failed: {e}")
        return _fallback_dossier(query, 0, str(e))


def _fallback_dossier(query: str, tokens_used: int = 0, error: str = None) -> Dict:
    """Dossier de secours en cas d'erreur"""
    return {
        "sections": [
            {
                "title": "Résumé",
                "content": f"Analyse pour: {query}" + (f" (Erreur: {error})" if error else ""),
                "evidence_refs": [],
            },
        ],
        "summary": f"Dossier partiel pour: {query}",
        "key_findings": ["Analyse incomplète - documents insuffisants"],
        "recommendations": ["Relancer avec plus de sources"],
        "quality_score": 20,
        "quality_breakdown": {
            "completeness": 20,
            "source_quality": 30,
            "relevance": 30,
        },
        "tokens_used": tokens_used,
        "model_used": "gpt-4o",
        "evidence": [],
    }


# ================================================================
# FETCH HELPERS
# ================================================================

def _fetch_plan_urls(
    db: Session, 
    dossier_id: UUID, 
    lead_item_id: UUID, 
    urls: List[str],
    log: TaskLogger = None,
) -> List[Dict]:
    """Fetch all URLs from the plan and store as SourceDocuments"""
    if log is None:
        log = get_task_logger("http")
    
    docs = []
    for idx, url in enumerate(urls[:10], 1):  # Limit to 10 URLs
        print(f"{Colors.GRAY}      [{idx}/{min(len(urls), 10)}] Fetching: {url[:60]}...{Colors.RESET}", flush=True)
        doc = _fetch_single_url(db, dossier_id, lead_item_id, url, log)
        if doc:
            docs.append(doc)
            print(f"{Colors.GREEN}         ✓ OK ({len(doc.get('content', ''))} chars){Colors.RESET}", flush=True)
        else:
            print(f"{Colors.RED}         ✗ FAIL{Colors.RESET}", flush=True)
    return docs


def _fetch_single_url(
    db: Session,
    dossier_id: UUID,
    lead_item_id: UUID,
    url: str,
    log: TaskLogger = None,
) -> Optional[Dict]:
    """Fetch a single URL and store as SourceDocument"""
    import requests
    
    if log is None:
        log = get_task_logger("http")
    
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Radar Bot"
        })
        response.raise_for_status()
        
        content = response.text[:50000]  # Limit size
        
        doc = SourceDocumentV2(
            url=url,
            dossier_id=dossier_id,
            lead_item_id=lead_item_id,
            raw_html=content,
            fetched_at=datetime.utcnow(),
        )
        db.add(doc)
        db.flush()
        
        return {
            "id": str(doc.id),
            "url": url,
            "content": content,
        }
        
    except Exception as e:
        log.warning(f"Échec fetch {url[:50]}: {e}")
        return None


# ================================================================
# UTILITIES
# ================================================================

def _log(db: Session, collection_id: str, level: str, message: str):
    """Log a message for a collection - both console and DB"""
    # Console log via TaskLogger
    log = get_task_logger("db", collection_id=collection_id)
    if level == "info":
        log.info(message)
    elif level == "error":
        log.error(message)
    elif level == "warning":
        log.warning(message)
    else:
        log.debug(message)
    
    # DB log
    log_entry = CollectionLog(
        collection_id=collection_id,
        level=level,
        message=message,
    )
    db.add(log_entry)
    db.commit()


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string to datetime"""
    if not date_str:
        return None
    
    from dateutil import parser
    try:
        return parser.parse(date_str)
    except:
        return None
