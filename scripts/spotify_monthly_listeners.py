"""Read a published monthly listener count without an API key or browser.
Usage: PYTHONPATH=backend python scripts/spotify_monthly_listeners.py SPOTIFY_ARTIST_ID_OR_URL
"""
import argparse
import json
import re
from urllib.parse import urlparse
from app.enrichment.providers.spotify_scraper import scrape_spotify_artist


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artist', help='Spotify artist ID or public open.spotify.com artist URL')
    args = parser.parse_args()
    artist_id = args.artist
    if artist_id.startswith('https://'):
        url = urlparse(artist_id)
        parts = url.path.strip('/').split('/')
        if url.hostname != 'open.spotify.com' or url.username or url.password or len(parts) < 2 or parts[-2] != 'artist':
            parser.error('Expected a public Spotify artist URL')
        artist_id = parts[-1]
    if not re.fullmatch(r'[A-Za-z0-9]{22}',artist_id):
        parser.error('Expected a 22-character Spotify artist ID')
    result = scrape_spotify_artist(artist_id)
    print(json.dumps(result or {'spotify_artist_id':artist_id, 'status':'unavailable'},ensure_ascii=False,indent=2))
    return 0 if result else 1


if __name__=='__main__':
    raise SystemExit(main())
