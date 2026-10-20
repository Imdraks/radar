"""Collect public Spotify artist statistics without an API key or a browser.

Only the requested artist's embedded entity is accepted. Rounded SEO descriptions
are never promoted to exact observations. No private endpoints or session tokens.
"""
import base64
import binascii
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import httpx
from bs4 import BeautifulSoup
from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)
PUBLIC_CACHE_TTL = 12 * 3600
MAX_PAGE_BYTES = 2_000_000
PARSER_VERSION = "spotify-public-state-v1"


def parse_spotify_artist_page(content: str, spotify_id: str) -> Optional[Dict[str, Any]]:
    """Parse only the exact artist entity, never recommended artists or rounded SEO."""
    if not re.fullmatch(r"[A-Za-z0-9]{22}", spotify_id) or len(content) > MAX_PAGE_BYTES:
        return None
    soup = BeautifulSoup(content, "html.parser")
    state_tag = soup.find("script", id="initialState")
    if state_tag is None:
        return None
    try:
        encoded = state_tag.get_text().strip()
        # Current public pages encode the state as base64 JSON.
        state = json.loads(base64.b64decode(encoded, validate=True))
        uri = f"spotify:artist:{spotify_id}"
        artist = state["entities"]["items"][uri]
        if artist.get("uri") != uri:
            return None
        listeners = artist.get("stats", {}).get("monthlyListeners")
        # bool is an int subclass; floats/strings/negative values are not exact counts.
        if type(listeners) is not int or listeners < 0:
            return None
        name = artist.get("profile", {}).get("name")
        image = soup.find("meta", property="og:image")
        return {
            "spotify_artist_id": spotify_id,
            "name": name,
            "image_url": image.get("content") if image else None,
            "monthly_listeners": listeners,
            "monthly_listeners_source": "spotify_public",
            "monthly_listeners_estimated": False,
            "source_url": f"https://open.spotify.com/artist/{spotify_id}",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "metric_window_days": 28,
            "precision": "integer_published_by_source",
            "parser_version": PARSER_VERSION,
        }
    except (ValueError, TypeError, KeyError, AttributeError, binascii.Error):
        return None


def scrape_spotify_artist(spotify_id: str) -> Optional[Dict[str, Any]]:
    """Fetch public HTML with bounded time/size and cache observations for 12 hours.

    Failures and changes of page structure remain unavailable, never estimated.
    Access denial/rate limiting stops here: no proxy rotation or private API fallback.
    """
    if not isinstance(spotify_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", spotify_id):
        return None
    key = f"spotify-public-page:v1:{spotify_id}"
    cached = cache_get(key)
    if cached:
        return None if cached.get("unavailable") else cached
    if cache_get("spotify-public-page:cooldown"):
        return None
    try:
        with httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False) as client:
            with client.stream("GET", f"https://open.spotify.com/artist/{spotify_id}", headers={
                "User-Agent": "Radar/1.0 (+https://radarapp.fr)",
                "Accept-Language": "en-US", "Accept": "text/html",
            }) as response:
                if response.status_code != 200:
                    logger.warning("Spotify public page unavailable (%s) for %s", response.status_code, spotify_id)
                    if response.status_code == 429:
                        cache_set("spotify-public-page:cooldown", True, ttl=900)
                    cache_set(key, {"unavailable": True}, ttl=900)
                    return None
                if "text/html" not in response.headers.get("content-type", "").lower():
                    return None
                content = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    content.extend(chunk)
                    if len(content) > MAX_PAGE_BYTES:
                        return None
                result = parse_spotify_artist_page(content.decode("utf-8", errors="replace"), spotify_id)
        cache_set(key, result or {"unavailable": True}, ttl=PUBLIC_CACHE_TTL if result else 900)
        return result
    except httpx.HTTPError:
        logger.warning("Spotify public page request failed for %s", spotify_id, exc_info=True)
        return None


def _search_musicbrainz(name: str) -> Optional[str]:
    """
    Find Spotify artist ID via MusicBrainz (free, reliable, no auth).
    MusicBrainz stores external links (url-rels) including Spotify URLs.
    Rate limit: 1 request/second, requires User-Agent.
    """
    import time
    try:
        import httpx
        headers = {"User-Agent": "RadarApp/1.0 (contact@radarapp.fr)"}

        # Step 1: Search for artist by name
        r = httpx.get(
            "https://musicbrainz.org/ws/2/artist/",
            params={"query": name, "fmt": "json", "limit": 5},
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200:
            logger.warning(f"MusicBrainz search HTTP {r.status_code} for '{name}'")
            return None

        artists = r.json().get("artists", [])
        if not artists:
            logger.warning(f"MusicBrainz: no results for '{name}'")
            return None

        # Pick best match: prefer exact name match with high score
        name_lower = name.lower().strip()
        best = None
        for a in artists:
            if a.get("name", "").lower().strip() == name_lower and a.get("score", 0) >= 80:
                best = a
                break
        if not best:
            # Fallback to highest score if >= 90
            top = artists[0]
            if top.get("score", 0) >= 90:
                best = top
        if not best:
            logger.warning(f"MusicBrainz: no confident match for '{name}' (top score: {artists[0].get('score')})")
            return None

        mbid = best["id"]
        logger.info(f"MusicBrainz matched '{name}' → '{best['name']}' (score={best.get('score')}, mbid={mbid})")

        # Step 2: Get external URLs (url-rels) — respect rate limit
        time.sleep(1.1)
        r2 = httpx.get(
            f"https://musicbrainz.org/ws/2/artist/{mbid}",
            params={"inc": "url-rels", "fmt": "json"},
            headers=headers,
            timeout=10,
        )
        if r2.status_code != 200:
            logger.warning(f"MusicBrainz url-rels HTTP {r2.status_code} for mbid={mbid}")
            return None

        for rel in r2.json().get("relations", []):
            url = rel.get("url", {}).get("resource", "")
            if "open.spotify.com/artist/" in url:
                spotify_id = url.split("/artist/")[-1].split("?")[0]
                if re.match(r"^[a-zA-Z0-9]{22}$", spotify_id):
                    logger.info(f"MusicBrainz found Spotify ID for '{name}': {spotify_id}")
                    return spotify_id

        logger.warning(f"MusicBrainz: no Spotify URL for '{name}' (mbid={mbid})")
        return None

    except Exception as e:
        logger.warning(f"MusicBrainz search failed for '{name}': {e}")
        return None


def search_spotify_id_by_name(name: str) -> Optional[str]:
    """
    Find a Spotify artist ID by name.
    Strategy: MusicBrainz (primary) → Google search (fallback).
    
    Returns the Spotify artist ID (22 chars) or None.
    """
    # Primary: MusicBrainz (free, reliable, structured data)
    spotify_id = _search_musicbrainz(name)
    if spotify_id:
        return spotify_id

    # Fallback: Google search
    try:
        import httpx
        query = f'site:open.spotify.com/artist "{name}"'
        r = httpx.get(
            "https://www.google.com/search",
            params={"q": query, "num": 5},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=10,
            follow_redirects=True,
        )
        ids = re.findall(r'open\.spotify\.com/artist/([a-zA-Z0-9]{22})', r.text)
        if ids:
            from collections import Counter
            best_id = Counter(ids).most_common(1)[0][0]
            logger.info(f"Google fallback found Spotify ID for '{name}': {best_id}")
            return best_id
    except Exception as e:
        logger.warning(f"Google fallback failed for '{name}': {e}")

    logger.warning(f"No Spotify ID found for '{name}' via any source")
    return None
