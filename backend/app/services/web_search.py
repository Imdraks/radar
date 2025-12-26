"""
Web Search Service - Real-time web search for AI collection.
Uses Tavily API for intelligent web search with AI-optimized results.
Falls back to DuckDuckGo if Tavily is not configured.
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for performing real web searches"""
    
    def __init__(self):
        self.tavily_api_key = getattr(settings, 'tavily_api_key', None)
        self.serp_api_key = getattr(settings, 'serp_api_key', None)
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        search_depth: str = "advanced",
        include_domains: List[str] = None,
        exclude_domains: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform a web search and return structured results.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_depth: "basic" or "advanced" (Tavily)
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            
        Returns:
            Dict with 'results' list and 'answer' summary
        """
        # Try Tavily first (best for AI applications)
        if self.tavily_api_key:
            return await self._search_tavily(
                query, max_results, search_depth, 
                include_domains, exclude_domains
            )
        
        # Fallback to DuckDuckGo (free, no API key needed)
        return await self._search_duckduckgo(query, max_results)
    
    async def _search_tavily(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        include_domains: List[str] = None,
        exclude_domains: List[str] = None,
    ) -> Dict[str, Any]:
        """Search using Tavily API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": False,
                }
                
                if include_domains:
                    payload["include_domains"] = include_domains
                if exclude_domains:
                    payload["exclude_domains"] = exclude_domains
                
                response = await client.post(
                    "https://api.tavily.com/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "success": True,
                    "source": "tavily",
                    "answer": data.get("answer", ""),
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "content": r.get("content", ""),
                            "score": r.get("score", 0),
                            "published_date": r.get("published_date"),
                        }
                        for r in data.get("results", [])
                    ]
                }
                
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            # Fallback to DuckDuckGo
            return await self._search_duckduckgo(query, max_results)
    
    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
    ) -> Dict[str, Any]:
        """Search using DuckDuckGo (free, no API key)"""
        try:
            # Use DuckDuckGo HTML search (no API key needed)
            async with httpx.AsyncClient(timeout=15.0) as client:
                # DuckDuckGo instant answer API
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1,
                    }
                )
                data = response.json()
                
                results = []
                
                # Get abstract if available
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "content": data.get("Abstract", ""),
                        "score": 1.0,
                        "source": data.get("AbstractSource", ""),
                    })
                
                # Get related topics
                for topic in data.get("RelatedTopics", [])[:max_results-1]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "url": topic.get("FirstURL", ""),
                            "content": topic.get("Text", ""),
                            "score": 0.8,
                        })
                
                return {
                    "success": True,
                    "source": "duckduckgo",
                    "answer": data.get("Abstract", ""),
                    "results": results[:max_results]
                }
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return {
                "success": False,
                "source": "none",
                "answer": "",
                "results": [],
                "error": str(e)
            }
    
    def search_sync(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
    ) -> Dict[str, Any]:
        """
        Synchronous version of search for use in Celery tasks.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.search(query, max_results, search_depth)
        )


def build_search_queries(
    entity_name: str,
    entity_type: str,
    objective: str,
    region: str = None,
    city: str = None,
    keywords: List[str] = None,
) -> List[str]:
    """
    Build multiple search queries for comprehensive results.
    
    Returns a list of queries to execute.
    """
    queries = []
    location = city or region or "France"
    
    objective_queries = {
        "SPONSOR": [
            f"{entity_name} sponsor partenariat marque",
            f"sponsoring événement musique {location} 2024 2025",
            f"marques partenaires festivals concerts {location}",
            f"budget marketing sponsoring culturel {location}",
        ],
        "BOOKING": [
            f"programmateur artistique {location}",
            f"directeur artistique festival {location} 2025",
            f"booking agent musique {location}",
            f"appel à candidature festival concert {location} 2025",
        ],
        "PRESS": [
            f"journaliste musique culture {location}",
            f"attaché de presse musique",
            f"média musical blog {location}",
            f"contact presse festival concert",
        ],
        "VENUE": [
            f"salle concert {location} location",
            f"lieu événementiel {location} capacité",
            f"SMAC scène musique {location}",
            f"programmation salle concert {location} 2025",
        ],
        "GRANT": [
            f"subvention aide projet musical {location} 2025",
            f"appel à projet musique {location}",
            f"financement artiste musicien {location}",
            f"CNM aide artiste",
            f"DRAC subvention spectacle vivant {location}",
        ],
        "SUPPLIER": [
            f"prestataire technique son lumière {location}",
            f"location matériel scène concert {location}",
            f"backline location {location}",
        ],
    }
    
    # Add objective-specific queries
    queries.extend(objective_queries.get(objective, objective_queries["SPONSOR"]))
    
    # Add keyword-based queries
    if keywords:
        for kw in keywords[:3]:
            queries.append(f"{kw} {entity_name} {location}")
    
    return queries


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create the web search service singleton"""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
