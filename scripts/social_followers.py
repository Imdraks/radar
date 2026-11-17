"""Collect a public social counter with source and precision, without guessing handles.
Usage: PYTHONPATH=backend python scripts/social_followers.py instagram https://www.instagram.com/ARTIST/
For YouTube, configure YOUTUBE_API_KEY server-side (free quota).
"""
import argparse
import json
from app.enrichment.providers.social_public import PLATFORMS,fetch_social_counter,normalize_profile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform',choices=PLATFORMS)
    parser.add_argument('url')
    args=parser.parse_args()
    if not normalize_profile(args.platform,args.url):
        parser.error('Expected a public profile URL for this platform')
    result=fetch_social_counter(args.platform,args.url)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='collected' else 1


if __name__=='__main__':raise SystemExit(main())
