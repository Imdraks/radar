"""
AI-powered collection tasks using LLM + Real Web Search.
This handles the "Advanced Collection" that uses:
1. Real-time web search (Tavily/DuckDuckGo) for current information
2. LLM (Groq FREE / OpenAI) to analyze, structure and enrich the results

Supports:
- Groq (FREE, fast) - Llama 3.3 70B
- OpenAI (paid) - GPT-4o-mini
"""
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4

from openai import OpenAI

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.entity import (
    Entity, EntityType, Document, Brief, CollectionRun, 
    ObjectiveType, Contact, ContactType
)
from app.core.config import settings
from app.services.web_search import get_web_search_service, build_search_queries

logger = logging.getLogger(__name__)


def get_db():
    """Get database session"""
    return SessionLocal()


def get_llm_client() -> Tuple[Optional[OpenAI], str]:
    """
    Get LLM client - tries Groq first (free), then OpenAI.
    Returns (client, model_name)
    """
    # Try Groq first (FREE!)
    groq_api_key = getattr(settings, 'groq_api_key', None)
    if groq_api_key:
        logger.info("Using Groq (free) for AI collection")
        client = OpenAI(
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        return client, "llama-3.3-70b-versatile"
    
    # Fallback to OpenAI (paid)
    if settings.openai_api_key:
        logger.info("Using OpenAI for AI collection")
        client = OpenAI(api_key=settings.openai_api_key)
        return client, getattr(settings, 'openai_model', 'gpt-4o-mini')
    
    logger.warning("No LLM API key configured (GROQ_API_KEY or OPENAI_API_KEY)")
    return None, ""


# Keep old function for backward compatibility
def get_openai_client() -> Optional[OpenAI]:
    """Get OpenAI client if API key is configured"""
    client, _ = get_llm_client()
    return client


OBJECTIVE_PROMPTS = {
    "SPONSOR": """Tu es un expert en recherche de sponsors et partenaires.
Recherche des informations sur les sponsors potentiels, marques partenaires, et opportunités de partenariat pour {entity_name}.
Focus: budgets marketing, départements partenariats, contacts décisionnaires, historique de sponsoring.""",

    "BOOKING": """Tu es un expert en booking artistique.
Recherche des informations sur les opportunités de booking pour {entity_name}.
Focus: programmateurs, directeurs artistiques, dates disponibles, cachets, conditions techniques, contacts booking.""",

    "PRESS": """Tu es un expert en relations presse et médias.
Recherche des contacts presse, journalistes, et médias pertinents pour {entity_name}.
Focus: attachés de presse, journalistes culture/musique, médias spécialisés, émissions TV/radio.""",

    "VENUE": """Tu es un expert en recherche de lieux événementiels.
Recherche des salles, lieux de concerts, et espaces événementiels pour {entity_name}.
Focus: capacité, équipements techniques, tarifs de location, disponibilités, contacts booking.""",

    "SUPPLIER": """Tu es un expert en prestataires événementiels.
Recherche des prestataires techniques et logistiques pour {entity_name}.
Focus: son/lumière, scénographie, traiteur, sécurité, logistique, tarifs.""",

    "GRANT": """Tu es un expert en subventions et aides culturelles.
Recherche des subventions, appels à projets et aides disponibles pour {entity_name}.
Focus: montants, critères d'éligibilité, dates limites, contacts, documents requis."""
}


def build_search_prompt(
    entity_name: str,
    entity_type: str,
    objective: str,
    secondary_keywords: List[str],
    region: Optional[str] = None,
    city: Optional[str] = None,
    web_search_results: List[Dict[str, Any]] = None,
) -> str:
    """Build the search prompt for ChatGPT with web search context"""
    base_prompt = OBJECTIVE_PROMPTS.get(objective, OBJECTIVE_PROMPTS["SPONSOR"])
    base_prompt = base_prompt.format(entity_name=entity_name)
    
    location_context = ""
    if city:
        location_context = f"Zone géographique prioritaire: {city}"
    elif region:
        location_context = f"Zone géographique prioritaire: {region}"
    
    keywords_context = ""
    if secondary_keywords:
        keywords_context = f"Mots-clés additionnels à considérer: {', '.join(secondary_keywords)}"
    
    # Add web search results as context
    web_context = ""
    if web_search_results:
        web_context = "\n\n=== RÉSULTATS DE RECHERCHE WEB (informations actuelles) ===\n"
        for i, result in enumerate(web_search_results[:15], 1):
            web_context += f"\n[{i}] {result.get('title', 'Sans titre')}\n"
            web_context += f"    URL: {result.get('url', '')}\n"
            content = result.get('content', '')[:500]
            if content:
                web_context += f"    Contenu: {content}\n"
        web_context += "\n=== FIN DES RÉSULTATS WEB ===\n"
    
    full_prompt = f"""{base_prompt}

Entité recherchée: {entity_name} (type: {entity_type})
{location_context}
{keywords_context}
{web_context}

INSTRUCTIONS:
1. Analyse les résultats de recherche web ci-dessus pour extraire des informations pertinentes
2. Identifie les opportunités concrètes, contacts et informations utiles
3. Vérifie que les informations sont cohérentes et actuelles (2024-2025)
4. Priorise les résultats avec des contacts directs ou des deadlines proches

IMPORTANT: Retourne tes résultats au format JSON avec la structure suivante:
{{
  "summary": "Résumé exécutif de ta recherche basé sur les sources web (2-3 phrases)",
  "opportunities": [
    {{
      "title": "Titre de l'opportunité",
      "description": "Description détaillée",
      "organization": "Nom de l'organisation/entreprise",
      "relevance_score": 85,
      "contact_name": "Nom du contact (si trouvé)",
      "contact_role": "Rôle/fonction",
      "contact_email": "email@example.com (si trouvé)",
      "contact_phone": "+33... (si trouvé)",
      "budget_estimate": "Estimation budget si applicable",
      "deadline": "Date limite si applicable (format: YYYY-MM-DD)",
      "location": "Localisation",
      "source_url": "URL source de l'information",
      "source_info": "Nom de la source (site, article)",
      "action_items": ["Action recommandée 1", "Action 2"]
    }}
  ],
  "contacts": [
    {{
      "name": "Nom complet",
      "role": "Fonction/titre",
      "organization": "Organisation",
      "email": "email si trouvé",
      "phone": "téléphone si trouvé",
      "linkedin": "URL LinkedIn si trouvé",
      "source_url": "URL où le contact a été trouvé",
      "relevance": "Pourquoi ce contact est pertinent"
    }}
  ],
  "useful_facts": [
    "Fait important vérifié avec source",
    "Statistique ou info clé"
  ],
  "recommended_next_steps": [
    "Étape recommandée 1 (spécifique et actionnable)",
    "Étape recommandée 2"
  ]
}}

RÈGLES IMPORTANTES:
- Ne génère QUE des informations trouvées dans les sources web ou vérifiables
- Indique toujours la source (URL) pour chaque opportunité et contact
- Score de pertinence de 0 à 100 basé sur: présence de contact, deadline, budget, correspondance objectif
- Si une information est incertaine, indique "non confirmé" ou "à vérifier"
"""
    return full_prompt


def perform_web_search(
    entity_name: str,
    entity_type: str,
    objective: str,
    region: Optional[str] = None,
    city: Optional[str] = None,
    keywords: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Perform real web search to gather current information.
    Returns aggregated results from multiple queries.
    """
    search_service = get_web_search_service()
    
    # Build search queries
    queries = build_search_queries(
        entity_name=entity_name,
        entity_type=entity_type,
        objective=objective,
        region=region,
        city=city,
        keywords=keywords,
    )
    
    all_results = []
    seen_urls = set()
    
    for query in queries[:4]:  # Limit to 4 queries to avoid rate limits
        try:
            logger.info(f"Web search: {query}")
            search_results = search_service.search_sync(
                query=query,
                max_results=5,
                search_depth="basic",
            )
            
            if search_results.get("success"):
                for result in search_results.get("results", []):
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(result)
                        
        except Exception as e:
            logger.warning(f"Web search failed for query '{query}': {e}")
            continue
    
    logger.info(f"Web search completed: {len(all_results)} unique results")
    return all_results


def parse_ai_response(response_text: str) -> Dict[str, Any]:
    """Parse the AI response JSON"""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response JSON: {e}")
    
    # Return a basic structure if parsing fails
    return {
        "summary": response_text[:500] if response_text else "Aucun résultat",
        "opportunities": [],
        "contacts": [],
        "useful_facts": [],
        "recommended_next_steps": []
    }


def calculate_opportunity_score(opp: Dict[str, Any], objective: str) -> int:
    """Calculate a score for an AI-found opportunity"""
    score = opp.get('relevance_score', 50)
    
    # Bonus for having contact info
    if opp.get('contact_email'):
        score += 10
    if opp.get('contact_phone'):
        score += 5
    if opp.get('contact_name'):
        score += 5
    
    # Bonus for budget info
    if opp.get('budget_estimate'):
        score += 10
    
    # Bonus for deadline (urgency)
    if opp.get('deadline'):
        score += 5
    
    # Cap at 100
    return min(score, 100)


@celery_app.task(bind=True, max_retries=2)
def run_ai_collection_task(
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
    AI-powered collection task using ChatGPT.
    
    1. Build intelligent prompts based on entity and objective
    2. Query LLM (Groq FREE or OpenAI) for relevant opportunities
    3. Parse and score results
    4. Generate comprehensive brief
    """
    db = get_db()
    filters = filters or {}
    client, model_name = get_llm_client()
    
    try:
        # Get collection run
        collection_run = db.query(CollectionRun).filter(
            CollectionRun.id == run_id
        ).first()
        
        if not collection_run:
            logger.error(f"Collection run not found: {run_id}")
            return {"error": "Collection run not found"}
        
        # Check LLM availability
        if not client:
            collection_run.status = "FAILED"
            collection_run.error_summary = "No LLM API configured. Please set GROQ_API_KEY (free) or OPENAI_API_KEY."
            collection_run.finished_at = datetime.utcnow()
            db.commit()
            return {"error": "No LLM API key configured"}
        
        # Get entities
        entities = db.query(Entity).filter(
            Entity.id.in_([UUID(eid) for eid in entity_ids])
        ).all()
        
        if not entities:
            collection_run.status = "FAILED"
            collection_run.error_summary = "Entities not found"
            collection_run.finished_at = datetime.utcnow()
            db.commit()
            return {"error": "Entities not found"}
        
        logger.info(f"Starting AI collection for {len(entities)} entities with objective: {objective}")
        
        all_opportunities = []
        all_contacts = []
        all_facts = []
        all_steps = []
        summaries = []
        
        # Process each entity with ChatGPT
        for entity in entities:
            try:
                # Step 1: Perform real web search
                logger.info(f"Performing web search for entity: {entity.name}")
                web_results = perform_web_search(
                    entity_name=entity.name,
                    entity_type=entity.entity_type.value,
                    objective=objective,
                    region=filters.get('region'),
                    city=filters.get('city'),
                    keywords=secondary_keywords,
                )
                
                # Step 2: Build prompt with web search results
                prompt = build_search_prompt(
                    entity_name=entity.name,
                    entity_type=entity.entity_type.value,
                    objective=objective,
                    secondary_keywords=secondary_keywords or [],
                    region=filters.get('region'),
                    city=filters.get('city'),
                    web_search_results=web_results,
                )
                
                # Step 3: Call LLM to analyze and structure results
                logger.info(f"Analyzing results with {model_name} for entity: {entity.name}")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": """Tu es un assistant expert en recherche business et veille stratégique pour l'industrie musicale et événementielle.
Tu analyses des résultats de recherche web et en extrais des informations structurées, précises et actionnables.
Tu ne génères JAMAIS d'informations fictives - tu travailles uniquement avec les sources fournies.
Tu indiques toujours les sources (URLs) pour chaque information."""
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more factual responses
                    max_tokens=4000
                )
                
                response_text = response.choices[0].message.content
                parsed = parse_ai_response(response_text)
                
                # Collect results
                if parsed.get('summary'):
                    summaries.append(f"**{entity.name}**: {parsed['summary']}")
                
                for opp in parsed.get('opportunities', []):
                    opp['entity_name'] = entity.name
                    opp['entity_id'] = str(entity.id)
                    opp['score'] = calculate_opportunity_score(opp, objective)
                    all_opportunities.append(opp)
                
                for contact in parsed.get('contacts', []):
                    contact['entity_name'] = entity.name
                    contact['entity_id'] = str(entity.id)
                    all_contacts.append(contact)
                
                all_facts.extend(parsed.get('useful_facts', []))
                all_steps.extend(parsed.get('recommended_next_steps', []))
                
                # Store contacts in database
                for contact_data in parsed.get('contacts', []):
                    try:
                        # Determine contact type and value
                        if contact_data.get('email'):
                            c_type = ContactType.EMAIL
                            c_value = contact_data.get('email')
                        elif contact_data.get('phone'):
                            c_type = ContactType.PHONE
                            c_value = contact_data.get('phone')
                        else:
                            c_type = ContactType.AI_FOUND
                            c_value = contact_data.get('name', 'Unknown')
                        
                        # Build label from name, role and organization
                        label_parts = []
                        if contact_data.get('name'):
                            label_parts.append(contact_data.get('name'))
                        if contact_data.get('role'):
                            label_parts.append(contact_data.get('role'))
                        if contact_data.get('organization'):
                            label_parts.append(f"@ {contact_data.get('organization')}")
                        
                        contact = Contact(
                            entity_id=entity.id,
                            contact_type=c_type,
                            value=c_value,
                            label=" - ".join(label_parts) if label_parts else None,
                            source_name="AI Collection",
                            source_url=contact_data.get('source_url'),
                            reliability_score=80,
                        )
                        db.add(contact)
                    except Exception as e:
                        logger.warning(f"Failed to save contact: {e}")
                
            except Exception as e:
                logger.error(f"Error processing entity {entity.name}: {e}")
                continue
        
        # Filter by require_contact if needed
        if require_contact:
            all_opportunities = [
                opp for opp in all_opportunities 
                if opp.get('contact_email') or opp.get('contact_phone')
            ]
        
        # Sort by score
        all_opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Create brief for the first entity (or combined)
        main_entity = entities[0]
        
        brief = Brief(
            entity_id=main_entity.id,
            objective=ObjectiveType[objective],
            overview="\n\n".join(summaries) if summaries else "Collecte terminée",
            useful_facts=[
                {"fact": fact, "source": "AI Collection", "category": objective}
                for fact in all_facts[:10]
            ],
            timeline=[],  # Timeline events
            contacts_ranked=[
                {
                    "type": "email" if c.get('email') else "phone" if c.get('phone') else "other",
                    "value": c.get('email') or c.get('phone') or c.get('name'),
                    "label": f"{c.get('name', '')} - {c.get('role', '')} @ {c.get('organization', '')}",
                    "reliability_score": 0.8,
                    "source": c.get('source_url', 'AI Collection')
                }
                for c in all_contacts[:10]
            ],
            sources_used=[
                {"name": "ChatGPT AI + Web Search", "url": "", "document_count": len(all_opportunities)}
            ],
            document_count=len(all_opportunities),
            contact_count=len(all_contacts),
            completeness_score=min(1.0, 0.3 + len(all_opportunities) * 0.1),
            generated_at=datetime.utcnow(),
        )
        db.add(brief)
        db.flush()
        
        # Update collection run
        collection_run.status = "SUCCESS"
        collection_run.finished_at = datetime.utcnow()
        collection_run.documents_new = len(all_opportunities)
        collection_run.contacts_found = len(all_contacts)
        collection_run.brief_id = brief.id
        collection_run.sources_success = 1
        collection_run.source_runs = [{
            "source_id": None,  # AI source has no UUID
            "source_name": f"{model_name} AI",
            "status": "SUCCESS",
            "items_found": len(all_opportunities),
            "items_new": len(all_opportunities),
            "latency_ms": 0,
            "error": None
        }]
        
        db.commit()
        
        logger.info(f"AI collection completed: {len(all_opportunities)} opportunities, {len(all_contacts)} contacts")
        
        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "brief_id": str(brief.id),
            "opportunities_found": len(all_opportunities),
            "contacts_found": len(all_contacts),
        }
        
    except Exception as e:
        logger.error(f"AI collection task failed: {e}")
        if collection_run:
            collection_run.status = "FAILED"
            collection_run.error_summary = str(e)[:1000]
            collection_run.finished_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()
