"""Public social counters with explicit source precision; never infer profile handles."""
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from app.core.cache import cache_get, cache_set
from app.core.config import settings

PLATFORMS = ('instagram', 'tiktok', 'youtube')
METRICS = {'instagram':'instagram_followers', 'tiktok':'tiktok_followers', 'youtube':'youtube_subscribers'}
MAX_BYTES = 2_000_000
CACHE_TTL = 12 * 3600


def normalize_profile(platform, url):
    """Allow only public profile paths on fixed hosts; strip queries and fragments."""
    if platform not in PLATFORMS or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
        hosts = {'instagram':{'instagram.com','www.instagram.com'}, 'tiktok':{'tiktok.com','www.tiktok.com'},
                 'youtube':{'youtube.com','www.youtube.com'}}
        if parsed.scheme != 'https' or parsed.hostname not in hosts[platform] or parsed.username or parsed.password or parsed.port not in (None,443):
            return None
        path = parsed.path.strip('/')
        if platform == 'instagram' and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.]{0,29}',path) and path.lower() not in {'accounts','explore','reels','p','stories','direct','about','developer'}:
            return f'https://www.instagram.com/{path.lower()}/'
        if platform == 'tiktok' and re.fullmatch(r'@[A-Za-z0-9_][A-Za-z0-9_.]{0,23}',path):
            return f'https://www.tiktok.com/{path.lower()}'
        if platform == 'youtube' and (re.fullmatch(r'@[A-Za-z0-9_.-]{3,30}',path) or re.fullmatch(r'channel/UC[A-Za-z0-9_-]{22}',path)):
            return f'https://www.youtube.com/{path}'
    except ValueError:
        pass
    return None


def observation(platform, url, value=None, display_value=None, precision=None, status='unavailable', error_code=None):
    return {'platform':platform, 'metric':METRICS[platform], 'source_url':url, 'value':value,
            'display_value':display_value, 'precision':precision, 'status':status, 'error_code':error_code,
            'collected_at':datetime.now(timezone.utc).isoformat() if status == 'collected' else None,
            'checked_at':datetime.now(timezone.utc).isoformat(), 'parser_version':'social-public-v1'}


def parse_display_count(raw):
    """Normalize a published display value, retaining rounding metadata separately."""
    raw = raw.strip().replace('\u202f',' ').replace('\u00a0',' ')
    match = re.fullmatch(r'([0-9][0-9., ]*)([KMB])?',raw,re.I)
    if not match:
        return None
    number, suffix = match.groups()
    if suffix:
        number = number.replace(' ','').replace(',','.')
    else:
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:[, ]\d{3})+)',number):
            return None
        number = number.replace(',','').replace(' ','')
    try:
        value = Decimal(number) * {'K':1000,'M':1000000,'B':1000000000}.get((suffix or '').upper(),1)
        return int(value) if value >= 0 and value == value.to_integral_value() else None
    except InvalidOperation:
        return None


def parse_instagram(content, url):
    soup = BeautifulSoup(content,'html.parser')
    handle = urlparse(url).path.strip('/').lower()
    title = soup.find('meta',property='og:title')
    identity = title.get('content','') if title else soup.title.get_text() if soup.title else ''
    if not re.search(r'\(@'+re.escape(handle)+r'\)',identity,re.I):
        return observation('instagram',url,error_code='IDENTITY_OR_PAGE_UNAVAILABLE')
    tag = soup.find('meta',property='og:description')
    description = tag.get('content','') if tag else ''
    match = re.match(r'^([\d.,\s]+[KMB]?)\s+Followers\b',description,re.I)
    if not match:
        return observation('instagram',url,error_code='COUNTER_NOT_PUBLISHED')
    display = match.group(1).strip()
    value = parse_display_count(display)
    if value is None:
        return observation('instagram',url,error_code='INVALID_COUNTER')
    precision = 'rounded_public_display' if re.search('[KMB]',display,re.I) else 'published_integer_precision_unspecified'
    return observation('instagram',url,value,display,precision,'collected')


def parse_tiktok(content, url):
    soup = BeautifulSoup(content,'html.parser')
    tag = soup.find('script',id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
    try:
        state = json.loads(tag.get_text()) if tag else {}
        detail = state['__DEFAULT_SCOPE__']['webapp.user-detail']
        info = detail['userInfo']
        handle = urlparse(url).path.lstrip('/@')
        if type(detail.get('statusCode')) is not int or detail['statusCode'] != 0 or info['user']['uniqueId'].lower() != handle.lower():
            return observation('tiktok',url,error_code='PROFILE_UNAVAILABLE')
        count = info['stats']['followerCount']
        if type(count) is not int or count < 0:
            return observation('tiktok',url,error_code='INVALID_COUNTER')
        # An integer in the public payload is not a guarantee of unrounded internal data.
        return observation('tiktok',url,count,str(count),'published_integer_precision_unspecified','collected')
    except (ValueError,TypeError,KeyError,AttributeError):
        return observation('tiktok',url,error_code='PAGE_STRUCTURE_CHANGED')


def parse_youtube_api(data, url):
    """The official API rounds subscribers down to three significant figures."""
    try:
        if len(data['items']) != 1:
            return observation('youtube',url,error_code='CHANNEL_NOT_FOUND')
        channel = data['items'][0]
        path = urlparse(url).path.strip('/')
        if path.startswith('channel/'):
            valid = channel['id'] == path.split('/')[1]
        else:
            valid = channel['snippet'].get('customUrl','').lower() == path.lower()
        if not valid:
            return observation('youtube',url,error_code='IDENTITY_MISMATCH')
        stats = channel['statistics']
        if stats.get('hiddenSubscriberCount') is not False:
            return observation('youtube',url,error_code='COUNTER_NOT_PUBLIC')
        count = stats.get('subscriberCount')
        if not isinstance(count,str) or not re.fullmatch(r'\d{1,19}',count):
            return observation('youtube',url,error_code='INVALID_COUNTER')
        return observation('youtube',url,int(count),count,'rounded_down_3_significant_figures','collected')
    except (KeyError,TypeError,ValueError):
        return observation('youtube',url,error_code='INVALID_PROVIDER_RESPONSE')


def fetch_social_counter(platform, profile_url):
    url = normalize_profile(platform,profile_url)
    if not url:
        return observation(platform,None,error_code='NO_PROFILE_URL' if not profile_url else 'INVALID_PROFILE_URL')
    if platform == 'youtube' and not settings.youtube_api_key:
        return observation(platform,url,status='configuration_required',error_code='YOUTUBE_API_KEY_REQUIRED')
    key = f'social-public:v1:{platform}:{url}'
    cached = cache_get(key)
    if cached:
        return cached
    if cache_get(f'social-public:cooldown:{platform}'):
        return observation(platform,url,error_code='RATE_LIMITED')
    try:
        with httpx.Client(timeout=httpx.Timeout(15,connect=5),follow_redirects=False) as client:
            headers = {'User-Agent':'Radar/1.0 (+https://radarapp.fr)', 'Accept-Language':'en-US'}
            params = None
            target = url
            if platform == 'youtube':
                target = 'https://www.googleapis.com/youtube/v3/channels'
                path = urlparse(url).path.strip('/')
                params = {'part':'statistics,snippet', 'fields':'items(id,snippet(customUrl),statistics(subscriberCount,hiddenSubscriberCount))',
                          'id' if path.startswith('channel/') else 'forHandle':path.split('/')[-1]}
                # Keep credentials out of URLs, snapshots, caches and HTTP request logs.
                headers['X-Goog-Api-Key'] = settings.youtube_api_key
            with client.stream('GET',target,params=params,headers=headers) as response:
                if response.status_code != 200:
                    result = observation(platform,url,error_code=f'HTTP_{response.status_code}')
                    if response.status_code == 429:
                        retry = response.headers.get('Retry-After','')
                        delay = max(900,min(int(retry),2147483647)) if retry.isdigit() else 900
                        cache_set(f'social-public:cooldown:{platform}',True,ttl=delay)
                else:
                    content = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        content.extend(chunk)
                        if len(content) > MAX_BYTES:
                            return observation(platform,url,error_code='RESPONSE_TOO_LARGE')
                    if platform == 'youtube':
                        result = parse_youtube_api(json.loads(content),url)
                    elif 'text/html' in response.headers.get('content-type','').lower():
                        result = (parse_instagram if platform == 'instagram' else parse_tiktok)(content.decode('utf-8',errors='replace'),url)
                    else:
                        result = observation(platform,url,error_code='INVALID_CONTENT_TYPE')
        cache_set(key,result,ttl=CACHE_TTL if result['status']=='collected' else 900)
        return result
    except (httpx.HTTPError,ValueError):
        # Do not log request objects or provider credentials.
        result = observation(platform,url,error_code='NETWORK_OR_PROVIDER_UNAVAILABLE')
        cache_set(key,result,ttl=900)
        return result
