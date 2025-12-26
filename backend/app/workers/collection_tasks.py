"""
Celery tasks for entity-based collection system.
Handles collection runs, document fetching, extraction, and brief generation.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from celery import shared_task

from app.workers.celery_app import celery_app
from app.workers.task_logger import TaskLogger, get_task_logger, Colors
from app.db.session import SessionLocal
from app.db.models.source import SourceConfig
from app.db.models.entity import (
    Entity, Document, Extract, Contact, Brief, CollectionRun,
    ObjectiveType, ContactType, EntityType
)
from app.ingestion.factory import get_connector
from app.extraction.extraction_service import extraction_service, contact_scorer


def get_db():
    """Get database session"""
    return SessionLocal()


# ========================
# MAIN COLLECTION TASK
# ========================

@celery_app.task(bind=True, max_retries=1)
def run_collection_task(
    self,
    run_id: str,
    entity_ids: List[str],
    objective: str,
    secondary_keywords: List[str] = None,
    timeframe_days: int = 30,
    require_contact: bool = False,
    filters: Dict[str, Any] = None,
):
    """
    Main collection task that orchestrates the entire collection process.
    
    1. Fetch documents from all active sources
    2. Deduplicate and store documents
    3. Extract information from documents
    4. Generate/update briefs for entities
    """
    log = get_task_logger("collection", collection_id=run_id)
    log.step(f"Démarrage de la collecte", run_id=run_id)
    
    db = get_db()
    filters = filters or {}
    
    try:
        # Get collection run
        collection_run = db.query(CollectionRun).filter(
            CollectionRun.id == run_id
        ).first()
        
        if not collection_run:
            log.error(f"Collection run introuvable", run_id=run_id)
            return {"error": "Collection run not found"}
        
        # Get entities
        entities = db.query(Entity).filter(
            Entity.id.in_([UUID(eid) for eid in entity_ids])
        ).all()
        
        if not entities:
            log.error(f"Aucune entité trouvée", entity_ids=entity_ids)
            collection_run.status = "FAILED"
            collection_run.error_summary = "Entities not found"
            db.commit()
            return {"error": "Entities not found"}
        
        # Build search terms from entities and keywords
        search_terms = []
        for entity in entities:
            search_terms.append(entity.name)
            search_terms.extend(entity.aliases or [])
        search_terms.extend(secondary_keywords or [])
        
        log.info(f"Recherche pour {len(entities)} entités", terms=search_terms[:5])
        
        # Get active sources
        sources = db.query(SourceConfig).filter(SourceConfig.is_active == True).all()
        collection_run.source_count = len(sources)
        log.step(f"Récupération de {len(sources)} sources actives")
        
        source_runs = []
        total_new = 0
        total_updated = 0
        total_contacts = 0
        sources_success = 0
        sources_failed = 0
        
        # Process each source
        for idx, source in enumerate(sources, 1):
            source_log = get_task_logger("http", collection_id=run_id)
            start_time = time.time()
            
            print(f"{Colors.CYAN}   [{idx}/{len(sources)}] Source: {source.name} ({source.connector_type}){Colors.RESET}", flush=True)
            
            source_run = {
                "source_id": str(source.id),
                "source_name": source.name,
                "status": "RUNNING",
                "items_found": 0,
                "items_new": 0,
                "latency_ms": 0,
                "error": None
            }
            
            try:
                # Fetch from source
                connector = get_connector(source)
                source_log.debug(f"Connecteur créé: {type(connector).__name__}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    with log.timer(f"Fetch {source.name}"):
                        raw_items = loop.run_until_complete(connector.fetch())
                finally:
                    loop.close()
                
                source_run["items_found"] = len(raw_items)
                source_log.info(f"Récupéré {len(raw_items)} items de {source.name}")
                
                # Process each item
                for entity in entities:
                    new_docs, updated_docs, new_contacts = process_items_for_entity(
                        db=db,
                        raw_items=raw_items,
                        entity=entity,
                        source=source,
                        search_terms=search_terms,
                        objective=objective,
                        timeframe_days=timeframe_days,
                        log=log,
                    )
                    
                    source_run["items_new"] += new_docs
                    total_new += new_docs
                    total_updated += updated_docs
                    total_contacts += new_contacts
                
                source_run["status"] = "SUCCESS"
                sources_success += 1
                print(f"{Colors.GREEN}      ✓ {source.name}: {source_run['items_found']} items, {source_run['items_new']} nouveaux{Colors.RESET}", flush=True)
                
            except Exception as e:
                source_log.error(f"Erreur source {source.name}: {e}")
                source_run["status"] = "FAILED"
                source_run["error"] = str(e)[:500]
                sources_failed += 1
                print(f"{Colors.RED}      ✗ {source.name}: {e}{Colors.RESET}", flush=True)
            
            source_run["latency_ms"] = int((time.time() - start_time) * 1000)
            source_runs.append(source_run)
        
        # Update collection run
        collection_run.source_runs = source_runs
        collection_run.sources_success = sources_success
        collection_run.sources_failed = sources_failed
        collection_run.documents_new = total_new
        collection_run.documents_updated = total_updated
        collection_run.contacts_found = total_contacts
        collection_run.finished_at = datetime.utcnow()
        
        if sources_failed == 0:
            collection_run.status = "SUCCESS"
        elif sources_success > 0:
            collection_run.status = "PARTIAL"
        else:
            collection_run.status = "FAILED"
        
        db.commit()
        
        # Generate briefs for each entity (async)
        log.step("Lancement de la génération des briefs")
        for entity in entities:
            generate_brief_task.delay(
                entity_id=str(entity.id),
                objective=objective,
                timeframe_days=timeframe_days
            )
        
        log.success(
            f"Collecte terminée en {log.elapsed_str()}",
            new_docs=total_new,
            updated=total_updated,
            contacts=total_contacts,
            save=True
        )
        
        return {
            "run_id": run_id,
            "status": collection_run.status,
            "sources_success": sources_success,
            "sources_failed": sources_failed,
            "documents_new": total_new,
            "documents_updated": total_updated,
            "contacts_found": total_contacts,
        }
        
    except Exception as e:
        log.error(f"Collection task failed: {e}", save=True)
        if collection_run:
            collection_run.status = "FAILED"
            collection_run.error_summary = str(e)[:1000]
            collection_run.finished_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()


def process_items_for_entity(
    db,
    raw_items: List[Dict],
    entity: Entity,
    source: SourceConfig,
    search_terms: List[str],
    objective: str,
    timeframe_days: int,
    log: TaskLogger = None,
) -> tuple:
    """
    Process raw items, filter by relevance, deduplicate, and extract.
    Returns: (new_docs, updated_docs, new_contacts)
    """
    if log is None:
        log = get_task_logger("extractor")
    
    new_docs = 0
    updated_docs = 0
    new_contacts = 0
    
    # Filter items by search terms
    relevant_items = []
    for item in raw_items:
        text = f"{item.get('title', '')} {item.get('description', '')} {item.get('content', '')}".lower()
        if any(term.lower() in text for term in search_terms):
            relevant_items.append(item)
    
    log.debug(f"Filtrage: {len(relevant_items)}/{len(raw_items)} pertinents pour {entity.name}")
    
    for item in relevant_items:
        try:
            # Compute fingerprint for deduplication
            fingerprint = Document.compute_fingerprint(
                title=item.get('title', ''),
                url=item.get('url') or item.get('link'),
                published_date=item.get('published_at')
            )
            
            # Check if document exists
            existing_doc = db.query(Document).filter(
                Document.fingerprint == fingerprint
            ).first()
            
            if existing_doc:
                # Update if needed
                if not existing_doc.is_processed:
                    updated_docs += 1
                continue
            
            # Create new document
            document = Document(
                entity_id=entity.id,
                source_config_id=source.id,
                source_name=source.name,
                source_url=source.url,
                title=item.get('title', 'Sans titre')[:500],
                url=item.get('url') or item.get('link'),
                snippet=item.get('description', '')[:2000] if item.get('description') else None,
                full_content=item.get('content', '')[:50000] if item.get('content') else None,
                fingerprint=fingerprint,
                published_at=item.get('published_at'),
                fetched_at=datetime.utcnow(),
            )
            db.add(document)
            db.flush()
            new_docs += 1
            
            # Extract information (sync for now, could be async)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                extraction = loop.run_until_complete(
                    extraction_service.extract_document(
                        title=document.title,
                        content=document.full_content or document.snippet or "",
                        source_name=source.name,
                        url=document.url,
                        published_at=document.published_at,
                        entity_name=entity.name,
                        objective=objective
                    )
                )
            finally:
                loop.close()
            
            # Store extraction
            extract = Extract(
                document_id=document.id,
                summary=extraction.get("summary"),
                contacts_found=extraction.get("contacts_found", []),
                entities_found=extraction.get("entities_found", []),
                event_signals=extraction.get("event_signals", []),
                opportunity_type=ObjectiveType[extraction["opportunity_type"]] if extraction.get("opportunity_type") else None,
                confidence=extraction.get("confidence", 0.0),
                raw_json=extraction,
            )
            db.add(extract)
            
            # Process contacts
            for contact_data in extraction.get("contacts_found", []):
                contact_type_str = contact_data.get("type", "EMAIL").upper()
                try:
                    contact_type = ContactType[contact_type_str]
                except KeyError:
                    contact_type = ContactType.EMAIL
                
                value = contact_data.get("value", "").strip()
                if not value:
                    continue
                
                # Check if contact exists
                existing_contact = db.query(Contact).filter(
                    Contact.entity_id == entity.id,
                    Contact.contact_type == contact_type,
                    Contact.value == value
                ).first()
                
                if existing_contact:
                    # Update last seen
                    existing_contact.last_seen_at = datetime.utcnow()
                else:
                    # Score reliability
                    reliability = contact_scorer.score_contact(
                        contact_type=contact_type_str,
                        value=value,
                        source_url=document.url,
                        source_name=source.name,
                        is_official_source=contact_data.get("is_official", False),
                    )
                    
                    contact = Contact(
                        entity_id=entity.id,
                        contact_type=contact_type,
                        value=value,
                        label=contact_data.get("context"),
                        source_url=document.url,
                        source_name=source.name,
                        reliability_score=reliability,
                    )
                    db.add(contact)
                    new_contacts += 1
            
            document.is_processed = True
            document.processed_at = datetime.utcnow()
            
        except Exception as e:
            log.error(f"Erreur traitement item: {e}")
            continue
    
    if new_docs > 0:
        log.info(f"Entité {entity.name}: {new_docs} nouveaux docs, {new_contacts} contacts")
    
    db.commit()
    return new_docs, updated_docs, new_contacts


# ========================
# BRIEF GENERATION TASK
# ========================

@celery_app.task(bind=True)
def generate_brief_task(
    self,
    entity_id: str,
    objective: str,
    timeframe_days: int = 30,
):
    """
    Generate or update a brief for an entity.
    Aggregates all extractions and contacts to create a synthesized brief.
    """
    log = get_task_logger("gpt")
    log.step(f"Génération brief pour entité {entity_id[:8]}")
    
    db = get_db()
    
    try:
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity:
            log.error(f"Entité non trouvée", entity_id=entity_id)
            return {"error": "Entity not found"}
        
        log.info(f"Brief pour: {entity.name}", objective=objective)
        objective_enum = ObjectiveType[objective]
        
        # Get all extractions for this entity within timeframe
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        documents = db.query(Document).filter(
            Document.entity_id == entity.id,
            Document.is_processed == True,
        ).all()
        
        log.debug(f"Documents trouvés: {len(documents)}")
        
        extractions = []
        for doc in documents:
            for extract in doc.extracts:
                extractions.append({
                    "summary": extract.summary,
                    "contacts_found": extract.contacts_found,
                    "entities_found": extract.entities_found,
                    "event_signals": extract.event_signals,
                    "confidence": extract.confidence,
                    "source": doc.source_name,
                    "url": doc.url,
                    "date": doc.published_at.isoformat() if doc.published_at else None,
                })
        
        # Get existing contacts
        contacts = db.query(Contact).filter(
            Contact.entity_id == entity.id
        ).order_by(Contact.reliability_score.desc()).limit(20).all()
        
        existing_contacts = [
            {
                "contact_type": c.contact_type.value,
                "value": c.value,
                "label": c.label,
                "reliability_score": c.reliability_score,
                "source_name": c.source_name,
            }
            for c in contacts
        ]
        
        # Generate brief via LLM
        log.step("Appel GPT pour génération du brief")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with log.timer("GPT generate_brief"):
                brief_data = loop.run_until_complete(
                    extraction_service.generate_brief(
                        entity_name=entity.name,
                        entity_type=entity.entity_type.value,
                        objective=objective,
                        timeframe_days=timeframe_days,
                        extractions=extractions,
                        existing_contacts=existing_contacts,
                    )
                )
        finally:
            loop.close()
        
        # Check if brief exists for this entity+objective
        existing_brief = db.query(Brief).filter(
            Brief.entity_id == entity.id,
            Brief.objective == objective_enum
        ).first()
        
        if existing_brief:
            # Update existing brief
            existing_brief.overview = brief_data.get("overview")
            existing_brief.contacts_ranked = brief_data.get("contacts_ranked", [])
            existing_brief.useful_facts = brief_data.get("useful_facts", [])
            existing_brief.timeline = brief_data.get("timeline", [])
            existing_brief.completeness_score = brief_data.get("completeness_score", 0.0)
            existing_brief.document_count = len(documents)
            existing_brief.contact_count = len(contacts)
            existing_brief.generated_at = datetime.utcnow()
            existing_brief.sources_used = _aggregate_sources(documents)
            brief = existing_brief
        else:
            # Create new brief
            brief = Brief(
                entity_id=entity.id,
                objective=objective_enum,
                timeframe_days=timeframe_days,
                overview=brief_data.get("overview"),
                contacts_ranked=brief_data.get("contacts_ranked", []),
                useful_facts=brief_data.get("useful_facts", []),
                timeline=brief_data.get("timeline", []),
                sources_used=_aggregate_sources(documents),
                document_count=len(documents),
                contact_count=len(contacts),
                completeness_score=brief_data.get("completeness_score", 0.0),
            )
            db.add(brief)
        
        db.commit()
        
        log.success(f"Brief généré: {entity.name}", completeness=brief.completeness_score)
        
        return {
            "brief_id": str(brief.id),
            "entity_id": entity_id,
            "completeness_score": brief.completeness_score,
        }
        
    except Exception as e:
        log.error(f"Échec génération brief: {e}")
        raise
    finally:
        db.close()


def _aggregate_sources(documents: List[Document]) -> List[Dict]:
    """Aggregate source information from documents"""
    sources = {}
    for doc in documents:
        source_name = doc.source_name
        if source_name not in sources:
            sources[source_name] = {
                "name": source_name,
                "url": doc.source_url,
                "document_count": 0
            }
        sources[source_name]["document_count"] += 1
    
    return list(sources.values())
