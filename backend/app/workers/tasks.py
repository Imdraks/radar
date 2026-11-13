"""
Celery tasks for ingestion, scoring, and notifications
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.workers.task_logger import get_task_logger, Colors
from app.workers.progress_notifier import get_progress_notifier
from app.db.session import SessionLocal
from app.db.models.source import SourceConfig
from app.db.models.opportunity import Opportunity, OpportunityStatus, SourceType
from app.db.models.ingestion import IngestionRun, IngestionStatus
from app.ingestion.factory import get_connector
from app.extraction.extractor import DataExtractor
from app.extraction.deduplicator import Deduplicator
from app.scoring.engine import ScoringEngine
from app.workers.notifications import send_notifications

# Intelligence module
from app.intelligence import (
    IntelligenceEngine, 
    get_intelligence_engine,
    OpportunityGrade
)


def get_db() -> Session:
    """Get database session"""
    return SessionLocal()


def filter_items_by_search_params(items: List[Dict[str, Any]], search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter raw items based on search parameters.
    
    Args:
        items: List of raw items from connector
        search_params: Dictionary with keywords, region, city, budget_min, budget_max
    
    Returns:
        Filtered list of items
    """
    # Return all items if no search params or empty dict
    if not search_params:
        return items
    
    keywords = search_params.get('keywords', '')
    if keywords:
        keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
    else:
        keyword_list = []
    
    region = search_params.get('region', '').lower() if search_params.get('region') else None
    city = search_params.get('city', '').lower() if search_params.get('city') else None
    budget_min = search_params.get('budget_min')
    budget_max = search_params.get('budget_max')
    
    # If no actual filters are defined, return all items
    has_filters = keyword_list or region or city or budget_min is not None or budget_max is not None
    if not has_filters:
        print(f"{Colors.GRAY}[FILTER] Aucun filtre défini, retour de tous les items{Colors.RESET}", flush=True)
        return items
    
    filtered = []
    
    for item in items:
        # Get text content for keyword matching
        text_content = ' '.join([
            str(item.get('title', '')),
            str(item.get('description', '')),
            str(item.get('body', '')),
            str(item.get('content', '')),
            str(item.get('subject', '')),
        ]).lower()
        
        # Keyword filter
        if keyword_list:
            if not any(kw in text_content for kw in keyword_list):
                continue
        
        # Region filter
        if region:
            item_region = str(item.get('region', '') or '').lower()
            item_location = str(item.get('location', '') or '').lower()
            if region not in text_content and region not in item_region and region not in item_location:
                continue
        
        # City filter
        if city:
            item_city = str(item.get('city', '') or '').lower()
            item_location = str(item.get('location', '') or '').lower()
            if city not in text_content and city not in item_city and city not in item_location:
                continue
        
        # Budget filter
        item_budget = item.get('budget') or item.get('budget_max') or 0
        try:
            item_budget = float(item_budget) if item_budget else 0
        except (ValueError, TypeError):
            item_budget = 0
        
        if budget_min is not None and item_budget > 0 and item_budget < budget_min:
            continue
        if budget_max is not None and item_budget > budget_max:
            continue
        
        filtered.append(item)
    
    print(f"{Colors.CYAN}[FILTER] {len(items)} items → {len(filtered)} après filtrage{Colors.RESET}", flush=True)
    return filtered


def _get_result_message(run) -> str:
    """Generate a human-readable result message"""
    if run.items_new > 0:
        return f"{run.items_new} nouvelles opportunités trouvées"
    elif run.items_fetched == 0:
        return "Aucune donnée récupérée - la source est peut-être inaccessible"
    elif run.items_duplicate > 0:
        return f"Aucun nouveau résultat ({run.items_duplicate} doublons ignorés)"
    else:
        return "Aucun résultat correspondant aux critères de recherche"


@celery_app.task(bind=True, max_retries=2)
def run_ingestion_task(self, source_id: str, search_params: dict = None):
    """
    Run ingestion for a specific source.
    This is the main ingestion task.
    
    Args:
        source_id: The source configuration ID
        search_params: Optional search parameters (keywords, region, city, budget_min, budget_max)
    """
    log = get_task_logger("crawler")
    progress = get_progress_notifier(self.request.id)
    db = get_db()
    
    try:
        source = db.query(SourceConfig).filter(SourceConfig.id == source_id).first()
        if not source:
            log.error(f"Source non trouvée: {source_id}")
            progress.fail("Source not found")
            return {"error": "Source not found"}
        
        log.step(f"Ingestion: {source.name} ({source.source_type.value if source.source_type else 'unknown'})")
        progress.start(total_steps=4, message=f"Ingestion: {source.name}")
        
        # Create ingestion run record with search params in metadata
        run = IngestionRun(
            source_config_id=source.id,
            source_name=source.name,
            status=IngestionStatus.RUNNING,
            run_metadata={"search_params": search_params} if search_params else {},
        )
        db.add(run)
        db.commit()
        
        try:
            # Get connector and fetch data
            progress.step(1, f"Connexion à {source.name}")
            connector = get_connector(source)
            log.debug(f"Connecteur: {type(connector).__name__}")
            
            # Run async fetch in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                progress.step(2, f"Récupération des données de {source.name}")
                with log.timer(f"Fetch {source.name}"):
                    raw_items = loop.run_until_complete(connector.fetch())
            finally:
                loop.close()
            
            run.items_fetched = len(raw_items)
            log.info(f"Récupéré {len(raw_items)} items bruts")
            progress.progress(30, message=f"{len(raw_items)} items récupérés")
            
            # Log warning if no items fetched
            if len(raw_items) == 0:
                log.warning(f"⚠️ Aucun item trouvé sur {source.name} - vérifiez l'URL ou le format de la source")
            
            # Apply search filters if provided
            if search_params:
                original_count = len(raw_items)
                raw_items = filter_items_by_search_params(raw_items, search_params)
                log.info(f"Après filtrage: {len(raw_items)} items (sur {original_count})")
                if len(raw_items) == 0 and original_count > 0:
                    keywords = search_params.get('keywords', '')
                    log.warning(f"⚠️ Aucun résultat pour '{keywords}' dans {original_count} items de {source.name}")
            
            # Process items
            progress.step(3, "Extraction et déduplication")
            extractor = DataExtractor()
            deduplicator = Deduplicator(db)
            scoring_engine = ScoringEngine(db)
            
            new_opportunities = []
            total_items = len(raw_items)
            
            for idx, raw_item in enumerate(raw_items):
                # Update progress periodically
                if idx % 10 == 0 and total_items > 0:
                    pct = 40 + int((idx / total_items) * 40)  # 40% to 80%
                    progress.progress(pct, items_processed=idx, items_total=total_items)
                
                try:
                    # Extract structured data
                    extracted = extractor.extract_all(
                        raw_item,
                        source_type=source.source_type.value,
                        source_name=source.name
                    )
                    
                    # Check for duplicates
                    is_dup, existing, similarity = deduplicator.check_duplicate(
                        external_id=extracted['external_id'],
                        url=extracted.get('url_primary'),
                        title=extracted.get('title'),
                        organization=extracted.get('organization'),
                        deadline=extracted.get('deadline_at')
                    )
                    
                    if is_dup and existing:
                        run.items_duplicate += 1
                        continue
                    
                    # Create opportunity
                    opportunity = Opportunity(
                        external_id=extracted['external_id'],
                        source_type=SourceType(extracted['source_type']),
                        source_name=extracted['source_name'],
                        source_config_id=source.id,
                        title=extracted['title'],
                        category=extracted['category'],
                        organization=extracted.get('organization'),
                        description=extracted.get('description'),
                        snippet=extracted.get('snippet'),
                        url_primary=extracted.get('url_primary'),
                        urls_all=extracted.get('urls_all', []),
                        published_at=extracted.get('published_at'),
                        deadline_at=extracted.get('deadline_at'),
                        location_city=extracted.get('location_city'),
                        location_region=extracted.get('location_region'),
                        budget_amount=extracted.get('budget_amount'),
                        budget_hint=extracted.get('budget_hint'),
                        contact_email=extracted.get('contact_email'),
                        contact_phone=extracted.get('contact_phone'),
                        contact_url=extracted.get('contact_url'),
                        status=OpportunityStatus.NEW,
                    )
                    
                    # Check for possible duplicates
                    if similarity and similarity >= 0.7:
                        deduplicator.mark_possible_duplicate(opportunity, existing, similarity)
                    
                    # Calculate score
                    scoring_engine.score_opportunity(opportunity)
                    
                    db.add(opportunity)
                    new_opportunities.append(opportunity)
                    run.items_new += 1
                    
                except Exception as e:
                    log.error(f"Erreur traitement item: {e}")
                    run.items_error += 1
                    if not run.errors:
                        run.errors = []
                    run.errors.append(str(e)[:500])
            
            # Commit new opportunities
            db.commit()
            
            progress.step(4, "Finalisation")
            
            # Update source stats
            source.last_run_at = datetime.utcnow()
            source.next_run_at = datetime.utcnow() + timedelta(minutes=source.poll_interval_minutes)
            source.total_items_fetched += run.items_fetched
            
            # Handle connector errors
            if connector.get_errors():
                run.errors = (run.errors or []) + connector.get_errors()
            
            # Complete the run
            if run.items_error > 0 and run.items_new > 0:
                run.complete(IngestionStatus.PARTIAL)
            elif run.items_error > 0:
                run.complete(IngestionStatus.FAILED)
            else:
                run.complete(IngestionStatus.SUCCESS)
            
            db.commit()
            
            # Log result with clear message
            if run.items_new > 0:
                log.success(f"✅ {source.name}: {run.items_new} nouveaux, {run.items_duplicate} doublons")
            elif run.items_fetched == 0:
                log.warning(f"⚠️ {source.name}: Aucune donnée récupérée (source vide ou inaccessible)")
            elif run.items_duplicate > 0:
                log.info(f"ℹ️ {source.name}: {run.items_duplicate} doublons ignorés, aucun nouveau résultat")
            else:
                log.warning(f"⚠️ {source.name}: Aucun résultat correspondant aux critères de recherche")
            
            # Trigger notifications for high-score opportunities
            high_score_opps = [o for o in new_opportunities if o.score >= 10]
            if high_score_opps:
                check_and_send_notifications.delay()
            
            result = {
                "source": source.name,
                "status": run.status.value,
                "fetched": run.items_fetched,
                "new": run.items_new,
                "duplicate": run.items_duplicate,
                "errors": run.items_error,
                "message": _get_result_message(run)
            }
            
            # Send completion notification
            progress.complete(
                message=_get_result_message(run),
                result=result
            )
            
            return result
            
        except Exception as e:
            log.exception(f"Ingestion échouée pour {source.name}: {e}")
            progress.fail(str(e))
            run.complete(IngestionStatus.FAILED)
            run.errors = [str(e)[:500]]
            source.total_errors += 1
            source.last_error = str(e)[:500]
            source.last_error_at = datetime.utcnow()
            db.commit()
            raise self.retry(exc=e, countdown=60)
            
    finally:
        db.close()


@celery_app.task
def run_email_ingestion():
    """Run ingestion for all email sources"""
    db = get_db()
    try:
        sources = db.query(SourceConfig).filter(
            SourceConfig.is_active == True,
            SourceConfig.source_type == SourceType.EMAIL
        ).all()
        
        results = []
        for source in sources:
            result = run_ingestion_task.delay(str(source.id))
            results.append({"source": source.name, "task_id": result.id})
        
        return {"sources_triggered": len(results), "tasks": results}
    finally:
        db.close()


@celery_app.task
def run_web_ingestion():
    """Run ingestion for all web sources (RSS, HTML, API)"""
    db = get_db()
    try:
        sources = db.query(SourceConfig).filter(
            SourceConfig.is_active == True,
            SourceConfig.source_type.in_([SourceType.RSS, SourceType.HTML, SourceType.API])
        ).all()
        
        results = []
        for source in sources:
            result = run_ingestion_task.delay(str(source.id))
            results.append({"source": source.name, "task_id": result.id})
        
        return {"sources_triggered": len(results), "tasks": results}
    finally:
        db.close()


@celery_app.task
def run_all_ingestion():
    """Run ingestion for all active sources"""
    db = get_db()
    try:
        sources = db.query(SourceConfig).filter(
            SourceConfig.is_active == True
        ).all()
        
        results = []
        for source in sources:
            result = run_ingestion_task.delay(str(source.id))
            results.append({"source": source.name, "task_id": result.id})
        
        return {"sources_triggered": len(results), "tasks": results}
    finally:
        db.close()


@celery_app.task
def rescore_all_opportunities():
    """Rescore all opportunities (useful after rule changes)"""
    db = get_db()
    try:
        scoring_engine = ScoringEngine(db)
        
        opportunities = db.query(Opportunity).filter(
            Opportunity.status.notin_([
                OpportunityStatus.WON,
                OpportunityStatus.LOST,
                OpportunityStatus.ARCHIVED
            ])
        ).all()
        
        count = scoring_engine.rescore_all(opportunities)
        db.commit()
        
        return {"rescored": count, "total": len(opportunities)}
    finally:
        db.close()


@celery_app.task
def check_and_send_notifications():
    """Check for opportunities that need notifications"""
    from app.core.config import settings
    
    db = get_db()
    try:
        now = datetime.utcnow()
        
        # Find high-score new opportunities from last hour
        recent_high_score = db.query(Opportunity).filter(
            Opportunity.status == OpportunityStatus.NEW,
            Opportunity.score >= settings.notification_min_score,
            Opportunity.created_at >= now - timedelta(hours=1)
        ).all()
        
        # Find urgent opportunities (deadline soon + good score)
        urgent_deadline = db.query(Opportunity).filter(
            Opportunity.status.in_([OpportunityStatus.NEW, OpportunityStatus.REVIEW]),
            Opportunity.score >= settings.notification_urgent_min_score,
            Opportunity.deadline_at.isnot(None),
            Opportunity.deadline_at <= now + timedelta(days=settings.notification_urgent_days),
            Opportunity.deadline_at > now
        ).all()
        
        # Combine and deduplicate
        to_notify = {str(o.id): o for o in recent_high_score}
        for o in urgent_deadline:
            to_notify[str(o.id)] = o
        
        opportunities = list(to_notify.values())
        
        if opportunities:
            send_notifications(opportunities)
        
        return {"notified": len(opportunities)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def run_intelligent_search(self, query: str, search_params: Dict[str, Any] = None, source_ids: List[str] = None):
    """
    Run intelligent search with the AI-powered intelligence engine.
    
    This task uses the SmartCrawler, PriceExtractor, ContactExtractor, 
    ArtistAnalyzer, and OpportunityScorer to find and analyze opportunities.
    
    Args:
        query: Search query (e.g., "concert rap Paris", "PNL cachet")
        search_params: Optional parameters (budget_min, budget_max, region, city)
        source_ids: Optional list of source IDs to search from
    """
    import traceback
    log = get_task_logger("search")
    
    log.step(f"Recherche intelligente: {query}")
    print(f"\n{'='*80}", flush=True)
    print(f"🔍 RECHERCHE INTELLIGENTE - DÉMARRAGE", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"   Query: {query}", flush=True)
    print(f"   Params: {search_params}", flush=True)
    print(f"   Source IDs: {source_ids}", flush=True)
    print(f"   Task ID: {self.request.id}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    db = get_db()
    
    try:
        # Create ingestion run
        run = IngestionRun(
            source_config_id=None,
            source_name=f"Intelligent Search: {query[:50]}",
            status=IngestionStatus.RUNNING,
            run_metadata={
                "query": query,
                "search_params": search_params,
                "source_ids": source_ids,
                "type": "intelligent_search"
            },
        )
        db.add(run)
        db.commit()
        print(f"✅ IngestionRun créé: ID={run.id}", flush=True)
        
        try:
            # Get sources URLs
            source_urls = []
            if source_ids:
                sources = db.query(SourceConfig).filter(
                    SourceConfig.id.in_(source_ids),
                    SourceConfig.is_active == True
                ).all()
                source_urls = [s.url for s in sources if s.url]
            else:
                # Get all active sources
                sources = db.query(SourceConfig).filter(
                    SourceConfig.is_active == True
                ).all()
                source_urls = [s.url for s in sources if s.url]
            
            print(f"📡 Sources actives trouvées: {len(source_urls)}", flush=True)
            for i, url in enumerate(source_urls[:5]):
                print(f"   {i+1}. {url[:60]}...", flush=True)
            if len(source_urls) > 5:
                print(f"   ... et {len(source_urls) - 5} autres", flush=True)
            
            # Run intelligence engine
            print(f"\n🧠 Lancement du moteur d'intelligence...", flush=True)
            engine = get_intelligence_engine()
            print(f"   Engine type: {type(engine).__name__}", flush=True)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                print(f"   Appel de engine.search_and_analyze(query='{query}', sources={len(source_urls[:20])} URLs)...", flush=True)
                results = loop.run_until_complete(
                    engine.search_and_analyze(
                        query=query,
                        search_params=search_params or {},
                        sources=source_urls[:20]  # Max 20 sources
                    )
                )
                print(f"   ✅ Résultats reçus: {len(results.get('opportunities', []))} opportunités", flush=True)
            except Exception as engine_error:
                print(f"   ❌ ERREUR ENGINE: {engine_error}", flush=True)
                print(f"   {traceback.format_exc()}", flush=True)
                raise
            finally:
                loop.close()
            
            run.items_fetched = len(results.get('opportunities', []))
            
            # Process opportunities
            deduplicator = Deduplicator(db)
            scoring_engine = ScoringEngine(db)
            new_opportunities = []
            
            for opp_data in results.get('opportunities', []):
                try:
                    # Check for duplicates
                    is_dup, existing, similarity = deduplicator.check_duplicate(
                        external_id=opp_data.get('source_url', ''),
                        url=opp_data.get('source_url'),
                        title=opp_data.get('title'),
                        organization=None,
                        deadline=None
                    )
                    
                    if is_dup and existing:
                        run.items_duplicate += 1
                        continue
                    
                    # Create opportunity
                    opportunity = Opportunity(
                        external_id=f"intel_{datetime.utcnow().timestamp()}_{len(new_opportunities)}",
                        source_type=SourceType.HTML,
                        source_name=f"Intelligence: {query[:30]}",
                        title=opp_data.get('title', 'Opportunité Détectée'),
                        category="Intelligence",
                        description=opp_data.get('description', ''),
                        snippet=opp_data.get('description', '')[:500] if opp_data.get('description') else None,
                        url_primary=opp_data.get('source_url'),
                        location_city=opp_data.get('location'),
                        budget_amount=opp_data.get('budget'),
                        status=OpportunityStatus.NEW,
                    )
                    
                    # Set contact info if available
                    contacts = opp_data.get('contacts', [])
                    if contacts:
                        first_contact = contacts[0]
                        opportunity.contact_email = first_contact.get('email')
                        opportunity.contact_phone = first_contact.get('phone')
                    
                    # Use intelligent scoring result
                    intel_score = opp_data.get('scoring', {})
                    opportunity.score = int(intel_score.get('total_score', 0))
                    opportunity.score_breakdown = intel_score.get('breakdown', {})
                    
                    db.add(opportunity)
                    new_opportunities.append(opportunity)
                    run.items_new += 1
                    
                except Exception as e:
                    log.error(f"Erreur traitement résultat intelligent: {e}")
                    run.items_error += 1
            
            db.commit()
            
            # Complete the run
            if run.items_error > 0 and run.items_new > 0:
                run.complete(IngestionStatus.PARTIAL)
            elif run.items_error > 0:
                run.complete(IngestionStatus.FAILED)
            else:
                run.complete(IngestionStatus.SUCCESS)
            
            # Store additional results in metadata
            run.run_metadata.update({
                "summary": results.get('summary', {}),
                "artists_found": len(results.get('artists', [])),
                "contacts_found": len(results.get('contacts', [])),
                "prices_found": len(results.get('prices', [])),
            })
            
            db.commit()
            
            # Trigger notifications for high-score opportunities
            high_score_opps = [o for o in new_opportunities if o.score >= 10]
            if high_score_opps:
                check_and_send_notifications.delay()
            
            print(f"\n✅ RECHERCHE TERMINÉE AVEC SUCCÈS", flush=True)
            print(f"   Opportunités: {run.items_new}", flush=True)
            print(f"   Duplicates: {run.items_duplicate}", flush=True)
            print(f"   Erreurs: {run.items_error}", flush=True)
            print(f"   Artistes: {len(results.get('artists', []))}", flush=True)
            print(f"   Contacts: {len(results.get('contacts', []))}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            return {
                "query": query,
                "status": run.status.value,
                "opportunities_found": run.items_new,
                "duplicates": run.items_duplicate,
                "errors": run.items_error,
                "artists_found": len(results.get('artists', [])),
                "contacts_found": len(results.get('contacts', [])),
                "prices_found": len(results.get('prices', [])),
                "summary": results.get('summary', {}),
            }
            
        except Exception as e:
            print(f"\n❌ ERREUR RECHERCHE INTELLIGENTE: {e}", flush=True)
            print(f"   {traceback.format_exc()}", flush=True)
            log.exception(f"Recherche intelligente échouée: {query}")
            run.complete(IngestionStatus.FAILED)
            run.errors = [str(e)[:500]]
            db.commit()
            raise self.retry(exc=e, countdown=60)
            
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def analyze_artist_task(self, artist_name: str, force_refresh: bool = False, user_id: int = None, workspace_id: int = None):
    """
    Analyze an artist with AI-powered intelligence.
    
    Stage 1: Web Scanner
    - Spotify (monthly listeners)
    - YouTube (subscribers)
    - Wikipedia (bio)
    - Discogs (discography)
    - Songkick / Bandsintown (concerts)
    - Ticketmaster / Fnac (ticket prices)
    - Google (booking contacts)
    
    Stage 2: AI Intelligence Engine
    - Growth predictions (30/90/180 days)
    - SWOT analysis
    - Booking intelligence
    - Risk & opportunity assessment
    - Content strategy recommendations
    
    Args:
        artist_name: Name of the artist to analyze
        force_refresh: If True, rescan web even for known artists (to update data)
        user_id: Optional user ID who requested the analysis
    """
    import sys
    import traceback
    log = get_task_logger("gpt")
    
    log.step(f"Analyse artiste: {artist_name}")
    print(f"\n{'='*80}", flush=True)
    print(f"🎯 ANALYZE_ARTIST_TASK STARTED", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"   Artist: {artist_name}", flush=True)
    print(f"   Force Refresh: {force_refresh}", flush=True)
    print(f"   User ID: {user_id}", flush=True)
    print(f"   Task ID: {self.request.id}", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    try:
        from app.intelligence.web_artist_scanner import WebArtistScanner
        from app.intelligence.artist_intelligence_engine import ArtistIntelligenceEngine
        from app.db.models.artist_analysis import ArtistAnalysis
        
        print(f"✅ Imports réussis", flush=True)
        log.info(f"Début analyse AI pour: {artist_name}", force_refresh=force_refresh)
        
        # Stage 1: Web Scan
        log.step("Stage 1: Web Scan")
        print(f"\n📡 STAGE 1: WEB SCAN", flush=True)
        print(f"   Création de l'event loop asyncio...", flush=True)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def scan():
                print(f"   🔍 Ouverture du WebArtistScanner...", flush=True)
                async with WebArtistScanner() as scanner:
                    print(f"   🔍 Lancement du scan pour '{artist_name}'...", flush=True)
                    result = await scanner.scan_artist(artist_name, force_refresh=force_refresh)
                    print(f"   ✅ Scan terminé!", flush=True)
                    return result
            
            with log.timer("WebArtistScanner"):
                profile = loop.run_until_complete(scan())
            result = profile.to_dict()
            
            log.info(f"Scan terminé", tier=profile.market_tier, score=profile.popularity_score)
            print(f"\n   📊 RÉSULTATS DU SCAN:", flush=True)
            print(f"      Nom: {profile.name}", flush=True)
            print(f"      Tier: {profile.market_tier}", flush=True)
            print(f"      Score: {profile.popularity_score}", flush=True)
            print(f"      Spotify Monthly: {profile.spotify_monthly_listeners:,}", flush=True)
            print(f"      YouTube Subs: {profile.youtube_subscribers:,}", flush=True)
            print(f"      Instagram: {profile.instagram_followers:,}", flush=True)
            print(f"      TikTok: {profile.tiktok_followers:,}", flush=True)
            print(f"      Fee: {profile.estimated_fee_min:,.0f}€ - {profile.estimated_fee_max:,.0f}€", flush=True)
            print(f"      Sources: {profile.sources_scanned}", flush=True)
            
        except Exception as scan_error:
            log.error(f"Erreur scan: {scan_error}")
            print(f"\n   ❌ ERREUR SCAN: {scan_error}", flush=True)
            print(f"   Traceback: {traceback.format_exc()}", flush=True)
            raise
        finally:
            loop.close()
        
        # Stage 2: AI Intelligence Analysis
        log.step("Stage 2: AI Intelligence Engine")
        print(f"\n🧠 STAGE 2: AI INTELLIGENCE ENGINE", flush=True)
        ai_engine = ArtistIntelligenceEngine()
        
        with log.timer("ArtistIntelligenceEngine"):
            ai_report = ai_engine.analyze_artist(
                artist_name=profile.name,
                spotify_monthly_listeners=profile.spotify_monthly_listeners,
                spotify_followers=0,  # Will be enhanced later
                youtube_subscribers=profile.youtube_subscribers,
                instagram_followers=profile.instagram_followers,
                tiktok_followers=profile.tiktok_followers,
                genre=profile.genre or "default",
                country="FR",
            historical_data=None,  # Could add historical tracking later
            known_events=None,
            # Pass scanner's fee estimates (more reliable from known artists DB)
            scanner_fee_min=int(profile.estimated_fee_min) if profile.estimated_fee_min else None,
            scanner_fee_max=int(profile.estimated_fee_max) if profile.estimated_fee_max else None,
            scanner_tier=profile.market_tier,
        )
        
        # Convert AI report to dict for storage
        ai_report_dict = {
            "artist_name": ai_report.artist_name,
            "analysis_date": ai_report.analysis_date.isoformat(),
            "overall_score": ai_report.overall_score,
            "confidence_score": ai_report.confidence_score,
            "tier": ai_report.tier.value,
            "overall_trend": ai_report.overall_trend.value,
            "market_analysis": {
                "tier": ai_report.market_analysis.tier.value,
                "position": ai_report.market_analysis.position.value,
                "genre_rank_estimate": ai_report.market_analysis.genre_rank_estimate,
                "similar_artists": ai_report.market_analysis.similar_artists,
                "strengths": ai_report.market_analysis.strengths,
                "weaknesses": ai_report.market_analysis.weaknesses,
                "opportunities": ai_report.market_analysis.opportunities,
                "threats": ai_report.market_analysis.threats,
            },
            "listener_prediction": {
                "metric_name": ai_report.listener_prediction.metric_name,
                "current_value": ai_report.listener_prediction.current_value,
                "predicted_30d": ai_report.listener_prediction.predicted_value_30d,
                "predicted_90d": ai_report.listener_prediction.predicted_value_90d,
                "predicted_180d": ai_report.listener_prediction.predicted_value_180d,
                "confidence": ai_report.listener_prediction.confidence,
                "growth_rate_monthly": ai_report.listener_prediction.growth_rate_monthly,
                "trend": ai_report.listener_prediction.trend.value,
            },
            "social_prediction": {
                "metric_name": ai_report.social_prediction.metric_name,
                "current_value": ai_report.social_prediction.current_value,
                "predicted_30d": ai_report.social_prediction.predicted_value_30d,
                "predicted_90d": ai_report.social_prediction.predicted_value_90d,
                "predicted_180d": ai_report.social_prediction.predicted_value_180d,
                "confidence": ai_report.social_prediction.confidence,
                "growth_rate_monthly": ai_report.social_prediction.growth_rate_monthly,
                "trend": ai_report.social_prediction.trend.value,
            },
            "booking_intelligence": {
                "estimated_fee_min": ai_report.booking_intelligence.estimated_fee_min,
                "estimated_fee_max": ai_report.booking_intelligence.estimated_fee_max,
                "optimal_fee": ai_report.booking_intelligence.optimal_fee,
                "negotiation_power": ai_report.booking_intelligence.negotiation_power,
                "best_booking_window": ai_report.booking_intelligence.best_booking_window,
                "event_type_fit": ai_report.booking_intelligence.event_type_fit,
                "territory_strength": ai_report.booking_intelligence.territory_strength,
                "seasonal_demand": ai_report.booking_intelligence.seasonal_demand,
            },
            "content_strategy": {
                "best_platforms": ai_report.content_strategy.best_platforms,
                "posting_frequency": ai_report.content_strategy.posting_frequency,
                "engagement_rate": ai_report.content_strategy.engagement_rate,
                "viral_potential": ai_report.content_strategy.viral_potential,
                "content_recommendations": ai_report.content_strategy.content_recommendations,
                "collaboration_suggestions": ai_report.content_strategy.collaboration_suggestions,
            },
            "risk_score": ai_report.risk_score,
            "risk_factors": ai_report.risk_factors,
            "opportunity_score": ai_report.opportunity_score,
            "key_opportunities": ai_report.key_opportunities,
            "ai_summary": ai_report.ai_summary,
            "recommendations": ai_report.recommendations,
        }
        
        log.info(f"AI Score: {ai_report.overall_score:.1f}/100", tier=ai_report.tier.value, trend=ai_report.overall_trend.value)
        
        # Merge AI data into result
        result["ai_intelligence"] = ai_report_dict
        
        # Save to history with AI fields
        log.step("Sauvegarde en base de données")
        try:
            db = get_db()
            analysis = ArtistAnalysis(
                # Workspace isolation
                workspace_id=workspace_id,
                
                # Basic info
                artist_name=profile.name,
                real_name=profile.real_name,
                genre=profile.genre,
                image_url=profile.image_url,  # Photo de l'artiste
                
                # Social metrics
                spotify_monthly_listeners=profile.spotify_monthly_listeners or None,
                youtube_subscribers=profile.youtube_subscribers or None,
                instagram_followers=profile.instagram_followers or None,
                tiktok_followers=profile.tiktok_followers or None,
                total_followers=profile.total_followers,
                
                # Fees
                fee_min=profile.estimated_fee_min,
                fee_max=profile.estimated_fee_max,
                market_tier=profile.market_tier,
                popularity_score=profile.popularity_score,
                
                # Business
                record_label=profile.record_label,
                management=profile.management,
                booking_agency=profile.booking_agency,
                booking_email=profile.booking_email,
                market_trend=profile.market_trend,
                confidence_score=profile.confidence_score,
                
                # === AI Intelligence Fields ===
                ai_score=ai_report.overall_score,
                ai_tier=ai_report.tier.value,
                
                # Predictions
                growth_trend=ai_report.overall_trend.value,
                predicted_listeners_30d=ai_report.listener_prediction.predicted_value_30d,
                predicted_listeners_90d=ai_report.listener_prediction.predicted_value_90d,
                predicted_listeners_180d=ai_report.listener_prediction.predicted_value_180d,
                growth_rate_monthly=ai_report.listener_prediction.growth_rate_monthly,
                
                # SWOT
                strengths=ai_report.market_analysis.strengths,
                weaknesses=ai_report.market_analysis.weaknesses,
                opportunities=ai_report.market_analysis.opportunities,
                threats=ai_report.market_analysis.threats,
                
                # Booking Intelligence
                optimal_fee=ai_report.booking_intelligence.optimal_fee,
                negotiation_power=ai_report.booking_intelligence.negotiation_power,
                best_booking_window=ai_report.booking_intelligence.best_booking_window,
                event_type_fit=ai_report.booking_intelligence.event_type_fit,
                territory_strength=ai_report.booking_intelligence.territory_strength,
                seasonal_demand=ai_report.booking_intelligence.seasonal_demand,
                
                # Risk & Opportunity
                risk_score=ai_report.risk_score,
                risk_factors=ai_report.risk_factors,
                opportunity_score=ai_report.opportunity_score,
                key_opportunities=ai_report.key_opportunities,
                
                # Content Strategy
                best_platforms=ai_report.content_strategy.best_platforms,
                engagement_rate=ai_report.content_strategy.engagement_rate,
                viral_potential=ai_report.content_strategy.viral_potential,
                content_recommendations=ai_report.content_strategy.content_recommendations,
                
                # AI Summary
                ai_summary=ai_report.ai_summary,
                ai_recommendations=ai_report.recommendations,
                
                # Full data
                full_data=result,
                ai_report=ai_report_dict,
                sources_scanned=", ".join(profile.sources_scanned),
                analyzed_by_user_id=user_id,
            )
            db.add(analysis)
            db.commit()
            analysis_id = analysis.id
            log.success(f"Analyse sauvegardée", analysis_id=str(analysis_id))
            
            # === CREATE SNAPSHOT FOR PREDICTIONS ===
            try:
                from app.db.models.artist_snapshot import ArtistSnapshot
                
                snapshot = ArtistSnapshot(
                    artist_name=profile.name,
                    artist_name_normalized=ArtistSnapshot.normalize_name(profile.name),
                    workspace_id=workspace_id,
                    spotify_monthly_listeners=profile.spotify_monthly_listeners or None,
                    spotify_followers=profile.spotify_followers or None,
                    tiktok_followers=profile.tiktok_followers or None,
                    youtube_subscribers=profile.youtube_subscribers or None,
                    instagram_followers=profile.instagram_followers or None,
                    concerts_next_30d=None,  # No verified concert observation.
                    source_quality_score=None,  # Legacy confidence is not calibrated quality.
                    sources_used=None,  # A scan attempt is not a verified collected source.
                )
                db.add(snapshot)
                db.commit()
                log.info(f"Snapshot créé pour prédictions", artist=profile.name)
            except Exception as snap_err:
                log.warning(f"Échec création snapshot: {snap_err}")
                # Non-blocking - continue even if snapshot fails
                
        except Exception as e:
            log.error(f"Échec sauvegarde: {e}")
            analysis_id = None
        finally:
            db.close()
        
        log.success(f"Analyse terminée pour {artist_name}")
        return {
            "artist": artist_name,
            "status": "success",
            "analysis_id": analysis_id,
            "result": result,
            "ai_score": ai_report.overall_score,
            "ai_tier": ai_report.tier.value,
            "ai_summary": ai_report.ai_summary,
        }
        
    except Exception as e:
        print(f"\n❌ ERREUR GLOBALE: {e}", flush=True)
        print(f"   Traceback: {traceback.format_exc()}", flush=True)
        log.exception(f"Analyse artiste échouée: {artist_name}")
        raise self.retry(exc=e, countdown=30)


# ============================================
# CREATE RADAR FOLDER TASK
# ============================================

@celery_app.task(bind=True, max_retries=3)
def create_radar_folder_task(self, user_id: int):
    """
    Create Radar folder structure in Google Drive for a new user.
    Called after first SSO login.
    """
    import asyncio
    from app.services.google_workspace import GoogleWorkspaceService
    
    print(f"\n🗂️ Creating Radar folder for user {user_id}...", flush=True)
    
    async def create_folder():
        try:
            service = GoogleWorkspaceService(user_id)
            
            # Step 1: Find or create "Radar" folder at root
            radar_folder = await service.find_folder_by_name("Radar", parent_id=None)
            if radar_folder:
                print(f"   ✓ Radar folder already exists: {radar_folder['id']}", flush=True)
                radar_folder_id = radar_folder["id"]
            else:
                radar = await service.create_folder("Radar")
                radar_folder_id = radar["id"]
                print(f"   ✓ Created Radar folder: {radar_folder_id}", flush=True)
            
            # Step 2: Create subfolders inside Radar
            subfolders = ["Projets", "Archives", "Clients"]
            for subfolder_name in subfolders:
                existing = await service.find_folder_by_name(subfolder_name, radar_folder_id)
                if not existing:
                    await service.create_folder(subfolder_name, radar_folder_id)
                    print(f"   ✓ Created {subfolder_name} folder", flush=True)
            
            print(f"✅ Radar folder structure created for user {user_id}", flush=True)
            return {"success": True, "folder_id": radar_folder_id}
            
        except Exception as e:
            print(f"❌ Failed to create Radar folder: {e}", flush=True)
            raise
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(create_folder())
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Error creating Radar folder: {e}", flush=True)
        raise self.retry(exc=e, countdown=30)


# ============================================
# ENSURE DRIVE STRUCTURE TASK (NEW - IDEMPOTENT)
# ============================================

@celery_app.task(bind=True, max_retries=3)
def ensure_drive_structure_task(
    self,
    user_id: int,
    workspace_id: int,
    google_account_id: str
):
    """
    Ensure complete Drive folder structure exists for a workspace.
    Called at EVERY Google SSO login for idempotence.
    Creates/verifies folders based on workspace packs and addons.
    
    Args:
        user_id: User ID for token lookup
        workspace_id: Workspace ID  
        google_account_id: Google email/account ID
    """
    import asyncio
    from app.db.session import SessionLocal
    from app.services.drive_structure import ensure_drive_structure
    
    print(f"\n🗂️ Ensuring Drive structure for workspace {workspace_id}, user {user_id}...", flush=True)
    
    async def run_ensure():
        db = SessionLocal()
        try:
            result = await ensure_drive_structure(
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                google_account_id=google_account_id
            )
            
            print(f"   📁 Created: {len(result.created)} folders", flush=True)
            print(f"   🔄 Restored: {len(result.restored)} folders", flush=True)
            print(f"   ✓ Reused: {len(result.reused)} folders", flush=True)
            
            if result.errors:
                print(f"   ⚠️ Errors: {len(result.errors)}", flush=True)
                for err in result.errors:
                    print(f"      - {err}", flush=True)
            
            print(f"✅ Drive structure ensured for workspace {workspace_id}", flush=True)
            return result.to_dict()
            
        except Exception as e:
            print(f"❌ Failed to ensure Drive structure: {e}", flush=True)
            raise
        finally:
            db.close()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_ensure())
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Error ensuring Drive structure: {e}", flush=True)
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def ensure_project_drive_structure_task(
    self,
    user_id: int,
    workspace_id: int,
    google_account_id: str,
    project_id: int,
    project_name: str
):
    """
    Ensure project folder structure exists in Google Drive.
    Called when creating or opening a project.
    
    Args:
        user_id: User ID for token lookup
        workspace_id: Workspace ID
        google_account_id: Google email/account ID
        project_id: Project ID in database
        project_name: Project name for folder naming
    """
    import asyncio
    from app.db.session import SessionLocal
    from app.services.drive_structure import ensure_project_drive_structure
    
    print(f"\n📁 Ensuring Drive structure for project '{project_name}' (id={project_id})...", flush=True)
    
    async def run_ensure():
        db = SessionLocal()
        try:
            result = await ensure_project_drive_structure(
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                google_account_id=google_account_id,
                project_id=project_id,
                project_name=project_name
            )
            
            print(f"   📁 Created: {len(result.created)} folders", flush=True)
            print(f"   🔄 Restored: {len(result.restored)} folders", flush=True)
            print(f"   ✓ Reused: {len(result.reused)} folders", flush=True)
            
            if result.errors:
                print(f"   ⚠️ Errors: {len(result.errors)}", flush=True)
            
            print(f"✅ Project Drive structure ensured for '{project_name}'", flush=True)
            return result.to_dict()
            
        except Exception as e:
            print(f"❌ Failed to ensure project Drive structure: {e}", flush=True)
            raise
        finally:
            db.close()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_ensure())
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Error ensuring project Drive structure: {e}", flush=True)
        raise self.retry(exc=e, countdown=60)


# ============================================
# RETROACTIVE MIGRATION - ALL EXISTING USERS
# ============================================

@celery_app.task(bind=True)
def migrate_all_users_drive_structure(self):
    """
    Retroactive migration: Create Drive structure for ALL existing users.
    This task iterates through all users with Google tokens and ensures
    their Drive structure exists based on their workspace packs.
    
    Should be run once after deployment to catch up existing users.
    Can be safely re-run (idempotent).
    """
    from app.db.session import SessionLocal
    from app.db.models.user import User
    from app.db.models.workspace import WorkspaceMember
    from app.db.models.account import Account
    from app.core.cache import cache_get
    
    print("\n" + "="*60, flush=True)
    print("🚀 RETROACTIVE MIGRATION: Drive Structure for ALL Users", flush=True)
    print("="*60, flush=True)
    
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(User).filter(User.is_active == True).all()
        print(f"\n📊 Found {len(users)} active users", flush=True)
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for user in users:
            try:
                # Check if user has Google tokens
                tokens = cache_get(f"google_workspace_tokens:{user.id}")
                if not tokens:
                    print(f"   ⏭️ User {user.email}: No Google tokens, skipping", flush=True)
                    skipped += 1
                    continue
                
                google_email = tokens.get("email", user.email)
                
                # Get user's workspaces
                memberships = db.query(WorkspaceMember).filter(
                    WorkspaceMember.user_id == user.id
                ).all()
                
                if not memberships:
                    print(f"   ⏭️ User {user.email}: No workspace membership, skipping", flush=True)
                    skipped += 1
                    continue
                
                # Queue drive structure task for each workspace
                for member in memberships:
                    print(f"   📁 Queueing Drive structure for user {user.email} in workspace {member.workspace_id}", flush=True)
                    ensure_drive_structure_task.delay(
                        user_id=user.id,
                        workspace_id=member.workspace_id,
                        google_account_id=google_email
                    )
                    migrated += 1
                    
            except Exception as e:
                print(f"   ❌ Error processing user {user.email}: {e}", flush=True)
                errors += 1
        
        print("\n" + "="*60, flush=True)
        print(f"✅ MIGRATION COMPLETE", flush=True)
        print(f"   📁 Queued: {migrated} workspace migrations", flush=True)
        print(f"   ⏭️ Skipped: {skipped} users (no tokens or workspace)", flush=True)
        print(f"   ❌ Errors: {errors}", flush=True)
        print("="*60 + "\n", flush=True)
        
        return {
            "success": True,
            "migrated": migrated,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        print(f"❌ Migration failed: {e}", flush=True)
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def migrate_user_drive_structure(self, user_id: int):
    """
    Migrate Drive structure for a single user.
    Useful for manual triggering or retry.
    
    Args:
        user_id: User ID to migrate
    """
    from app.db.session import SessionLocal
    from app.db.models.user import User
    from app.db.models.workspace import WorkspaceMember
    from app.core.cache import cache_get
    
    print(f"\n📁 Migrating Drive structure for user {user_id}...", flush=True)
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User {user_id} not found", flush=True)
            return {"success": False, "error": "User not found"}
        
        # Check if user has Google tokens
        tokens = cache_get(f"google_workspace_tokens:{user.id}")
        if not tokens:
            print(f"⏭️ User {user.email}: No Google tokens", flush=True)
            return {"success": False, "error": "No Google tokens"}
        
        google_email = tokens.get("email", user.email)
        
        # Get user's workspaces
        memberships = db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == user.id
        ).all()
        
        if not memberships:
            print(f"⏭️ User {user.email}: No workspace membership", flush=True)
            return {"success": False, "error": "No workspace membership"}
        
        # Queue drive structure task for each workspace
        queued = 0
        for member in memberships:
            ensure_drive_structure_task.delay(
                user_id=user.id,
                workspace_id=member.workspace_id,
                google_account_id=google_email
            )
            queued += 1
        
        print(f"✅ Queued {queued} workspace migrations for {user.email}", flush=True)
        return {"success": True, "queued": queued}
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def migrate_all_projects_drive_structure(self):
    """
    Retroactive migration: Create Drive structure for ALL existing projects.
    This ensures all projects have their Drive folders based on workspace packs.
    """
    from app.db.session import SessionLocal
    from app.db.models.agency import Project
    from app.db.models.workspace import Workspace, WorkspaceMember
    from app.core.cache import cache_get
    
    print("\n" + "="*60, flush=True)
    print("🚀 RETROACTIVE MIGRATION: Drive Structure for ALL Projects", flush=True)
    print("="*60, flush=True)
    
    db = SessionLocal()
    try:
        # Get all projects
        projects = db.query(Project).all()
        print(f"\n📊 Found {len(projects)} projects", flush=True)
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for project in projects:
            try:
                # Get workspace
                workspace = db.query(Workspace).filter(
                    Workspace.id == project.workspace_id
                ).first()
                
                if not workspace:
                    print(f"   ⏭️ Project '{project.name}': No workspace, skipping", flush=True)
                    skipped += 1
                    continue
                
                # Get a user with Google tokens from this workspace
                members = db.query(WorkspaceMember).filter(
                    WorkspaceMember.workspace_id == workspace.id
                ).all()
                
                user_with_tokens = None
                google_email = None
                
                for member in members:
                    tokens = cache_get(f"google_workspace_tokens:{member.user_id}")
                    if tokens:
                        user_with_tokens = member.user_id
                        google_email = tokens.get("email")
                        break
                
                if not user_with_tokens:
                    print(f"   ⏭️ Project '{project.name}': No user with Google tokens, skipping", flush=True)
                    skipped += 1
                    continue
                
                # Queue project structure task
                print(f"   📁 Queueing Drive structure for project '{project.name}'", flush=True)
                ensure_project_drive_structure_task.delay(
                    user_id=user_with_tokens,
                    workspace_id=workspace.id,
                    google_account_id=google_email,
                    project_id=project.id,
                    project_name=project.name
                )
                migrated += 1
                
            except Exception as e:
                print(f"   ❌ Error processing project '{project.name}': {e}", flush=True)
                errors += 1
        
        print("\n" + "="*60, flush=True)
        print(f"✅ PROJECT MIGRATION COMPLETE", flush=True)
        print(f"   📁 Queued: {migrated} project migrations", flush=True)
        print(f"   ⏭️ Skipped: {skipped} projects", flush=True)
        print(f"   ❌ Errors: {errors}", flush=True)
        print("="*60 + "\n", flush=True)
        
        return {
            "success": True,
            "migrated": migrated,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        print(f"❌ Migration failed: {e}", flush=True)
        raise
    finally:
        db.close()
