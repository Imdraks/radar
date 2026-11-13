"""Public page fixtures contain no provider tokens; network is mocked in the suite."""
import base64
import json
from unittest.mock import Mock
import httpx
import pytest
from app.enrichment.providers import spotify_scraper as scraper

HTTP_CLIENT = httpx.Client

ID = '4tZwfgrHOc3mvqYlEYSvVi'
OTHER = '1Xyo4u8uXC1ZmMpatF05PJ'


def html(count=1234567, uri=None):
    target = uri or f'spotify:artist:{ID}'
    state = {'entities':{'items':{
        f'spotify:artist:{OTHER}':{'uri':f'spotify:artist:{OTHER}', 'stats':{'monthlyListeners':99999999}},
        f'spotify:artist:{ID}':{'uri':target,'profile':{'name':'Test artist'},'stats':{'monthlyListeners':count}},
    }}}
    data = base64.b64encode(json.dumps(state).encode()).decode()
    return f'<html><meta property="og:description" content="Artist · 1.2M monthly listeners"><script id="initialState">{data}</script></html>'


@pytest.mark.parametrize('count', [0, 1234567, 116583387])
def test_parser_selects_requested_artist_not_recommendations(count):
    result = scraper.parse_spotify_artist_page(html(count), ID)
    assert result['monthly_listeners'] == count
    assert result['monthly_listeners_estimated'] is False
    assert result['monthly_listeners_source'] == 'spotify_public'
    assert result['source_url'].endswith(ID)
    assert result['collected_at']


@pytest.mark.parametrize('count', [None, -1, True, '1234567', 1234567.5])
def test_invalid_values_are_unavailable_not_estimated(count):
    assert scraper.parse_spotify_artist_page(html(count), ID) is None


def test_rounded_meta_wrong_identity_and_bad_state_are_not_observations():
    assert scraper.parse_spotify_artist_page('<meta property="og:description" content="1.2M monthly listeners">',ID) is None
    assert scraper.parse_spotify_artist_page(html(uri=f'spotify:artist:{OTHER}'),ID) is None
    assert scraper.parse_spotify_artist_page('<script id="initialState">not-json</script>',ID) is None
    assert scraper.parse_spotify_artist_page(html(), '../private') is None


@pytest.fixture
def public_cache(monkeypatch):
    cache = {}
    monkeypatch.setattr(scraper,'cache_get',lambda key:cache.get(key))
    monkeypatch.setattr(scraper,'cache_set',lambda key,value,ttl:cache.update({key:value}))
    return cache


def mock_http(monkeypatch, handler):
    original = HTTP_CLIENT
    monkeypatch.setattr(scraper.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))


def test_http_collection_is_keyless_and_cache_preserves_collection_date(monkeypatch,public_cache):
    calls = []
    def handle(request):
        calls.append(request)
        assert request.url.host == 'open.spotify.com'
        assert 'authorization' not in request.headers
        return httpx.Response(200,text=html(),headers={'Content-Type':'text/html; charset=utf-8'})
    mock_http(monkeypatch,handle)
    first = scraper.scrape_spotify_artist(ID)
    second = scraper.scrape_spotify_artist(ID)
    assert first == second and first['monthly_listeners'] == 1234567
    assert len(calls) == 1


@pytest.mark.parametrize('status',[302,401,403,404,429,500])
def test_denied_or_failed_pages_are_not_retried_or_followed(monkeypatch,public_cache,status):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status,headers={'Location':'https://example.com/private'})
    mock_http(monkeypatch,handle)
    assert scraper.scrape_spotify_artist(ID) is None
    assert scraper.scrape_spotify_artist(ID) is None
    assert len(calls) == 1
    if status == 429:
        assert public_cache['spotify-public-page:cooldown']
        assert scraper.scrape_spotify_artist(OTHER) is None
        assert len(calls) == 1


def test_large_non_html_and_timeout_responses_remain_unavailable(monkeypatch,public_cache):
    for response in [httpx.Response(200,text='x'*(scraper.MAX_PAGE_BYTES+1),headers={'Content-Type':'text/html'}),
                     httpx.Response(200,json={'monthlyListeners':123})]:
        public_cache.clear()
        mock_http(monkeypatch,lambda request:response)
        assert scraper.scrape_spotify_artist(ID) is None
    def timeout(request):
        raise httpx.ReadTimeout('timeout',request=request)
    public_cache.clear()
    mock_http(monkeypatch,timeout)
    assert scraper.scrape_spotify_artist(ID) is None


def test_search_worker_never_substitutes_followers_for_listeners(monkeypatch):
    from app.workers.spotify_search_pipeline import step_enrich
    monkeypatch.setattr('app.workers.spotify_search_pipeline.settings.viberate_enabled',False)
    monkeypatch.setattr(scraper,'scrape_spotify_artist',lambda artist_id:None)
    artist={'spotify_id':ID,'name':'Test','followers':99999999,'popularity':99}
    result=step_enrich(Mock(),Mock(),[artist])[0]
    assert result['monthly_listeners'] is None
    assert result['monthly_listeners_source'] == 'unavailable'


@pytest.mark.parametrize('observed',[None,{'monthly_listeners':1234567,'source_url':'https://open.spotify.com/artist/'+ID,'collected_at':'2026-10-20T00:00:00+00:00','precision':'integer_published_by_source'}])
def test_legacy_client_uses_observations_and_never_estimates(monkeypatch,observed):
    from app.intelligence.spotify_client import SpotifyClient
    client=object.__new__(SpotifyClient)
    # This method works even with no configured official API client.
    client.client=None
    monkeypatch.setattr(scraper,'scrape_spotify_artist',lambda artist_id:observed)
    assert client.get_monthly_listeners(ID) == (observed['monthly_listeners'] if observed else None)


@pytest.mark.asyncio
async def test_sync_and_async_search_keep_missing_counts_missing(monkeypatch):
    from app.intelligence.spotify_client import SpotifyClient
    client=object.__new__(SpotifyClient)
    client._enrichment_service=None
    client.client=Mock()
    artist={'id':ID,'name':'Test artist','followers':{'total':1234567},'popularity':99,'genres':[],
            'external_urls':{'spotify':'https://open.spotify.com/artist/'+ID},'images':[]}
    client.client.search.return_value={'artists':{'items':[artist]}}
    monkeypatch.setattr(client,'is_available',lambda:True)
    monkeypatch.setattr(client,'_find_best_match',lambda name,artists:artist)
    monkeypatch.setattr(scraper,'scrape_spotify_artist',lambda artist_id:None)
    for result in [client.search_artist('Test artist'),await client.search_artist_async('Test artist')]:
        assert result['monthly_listeners'] is None
        assert result['monthly_listeners_source'] == 'unavailable'
        assert result['estimated_monthly_listeners'] is None


@pytest.mark.parametrize('count',[0,1234567])
def test_discovery_snapshot_preserves_published_provenance(monkeypatch,db_session,actors,count,client,headers):
    from datetime import datetime,timedelta
    from app.db.models.discovery import DiscoveryArtist,DiscoveryEnrichmentJob,DiscoverySnapshot
    from app.workers.discovery_pipeline import step_spotify
    artist=DiscoveryArtist(workspace_id=actors[1][0].id,canonical_name='Test',normalized_name='test',spotify_artist_id=ID)
    db_session.add(artist);db_session.flush()
    job=DiscoveryEnrichmentJob(workspace_id=actors[1][0].id,artist_id=artist.id,input_type='SPOTIFY_URL',input_value=ID)
    db_session.add(job)
    db_session.add(DiscoverySnapshot(artist_id=artist.id,source='SPOTIFY',status='OK',
        parser_version='v4.0-scrape',raw_payload={'monthly_listeners':999999},
        fetched_at=datetime.utcnow()-timedelta(minutes=1),ttl_expires_at=datetime.utcnow()+timedelta(hours=12)))
    db_session.commit()
    observed=scraper.parse_spotify_artist_page(html(count),ID)
    monkeypatch.setattr(scraper,'scrape_spotify_artist',lambda artist_id:observed)
    monkeypatch.setattr('app.enrichment.providers.deezer.search_deezer_artist',lambda name:None)
    assert step_spotify(db_session,job) is True
    snapshot=db_session.query(DiscoverySnapshot).filter(DiscoverySnapshot.parser_version=='v5.1-public-links').one()
    assert snapshot.raw_payload['monthly_listeners']==count
    assert snapshot.raw_payload['source_url']==observed['source_url']
    assert snapshot.raw_payload['collected_at']==observed['collected_at']
    assert snapshot.raw_payload['monthly_listeners_source']=='spotify_public'
    actors[1][0].plan='premium'
    db_session.commit()
    response=client.get(f'/api/v1/discovery/artist/{artist.id}',headers=headers())
    assert response.status_code == 200,response.text
    evidence=next(item for item in response.json()['evidence'] if item['source']=='SPOTIFY')
    assert evidence['collected_at']==observed['collected_at']
    assert evidence['source_url']==observed['source_url']
