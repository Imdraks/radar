"""Social counter tests use minimal fixtures, never provider cookies or real API keys."""
import json
from datetime import datetime,timedelta
from unittest.mock import Mock
import httpx
import pytest
from app.enrichment.providers import social_public as social

HTTP_CLIENT = httpx.Client
IG = 'https://www.instagram.com/test.artist/'
TT = 'https://www.tiktok.com/@test.artist'
YT = 'https://www.youtube.com/@TestArtist'
CID = 'UC'+'a'*22


def instagram(display='1.2M',handle='test.artist'):
    return f'<meta property="og:title" content="Test (@{handle}) • Instagram"><meta property="og:description" content="{display} Followers, 1 Following, 10 Posts - Test">'


def tiktok(count=1234,handle='test.artist',status=0,private=False):
    state={'__DEFAULT_SCOPE__':{'webapp.user-detail':{'statusCode':status,'userInfo':{
        'user':{'uniqueId':handle,'privateAccount':private},'stats':{'followerCount':count,'heartCount':999999}}}}}
    return '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">'+json.dumps(state)+'</script>'


def youtube(count='123000',hidden=False,handle='@TestArtist'):
    return {'items':[{'id':CID,'snippet':{'customUrl':handle},'statistics':{'subscriberCount':count,'hiddenSubscriberCount':hidden}}]}


@pytest.mark.parametrize('platform,url',[
 ('instagram','http://www.instagram.com/test'),('instagram','https://instagram.com.evil.invalid/test'),
 ('instagram','https://user:password@www.instagram.com/test'),('instagram','https://www.instagram.com:444/test'),
 ('instagram','https://www.instagram.com/accounts/login'),('instagram','https://127.0.0.1/test'),
 ('tiktok','https://www.tiktok.com/@test/video/1'),('youtube','https://www.youtube.com/watch?v=abc'),
 ('youtube','https://www.youtube.com/redirect?q=https://127.0.0.1'),('youtube','https://youtu.be/abc'),
])
def test_only_fixed_public_profile_urls_are_accepted(platform,url):
    assert social.normalize_profile(platform,url) is None


def test_profile_canonicalization_strips_tracking_queries():
    assert social.normalize_profile('instagram','https://instagram.com/TEST.Artist/?utm_source=test') == IG
    assert social.normalize_profile('tiktok','https://tiktok.com/@Test.Artist/') == TT
    assert social.normalize_profile('youtube','https://www.youtube.com/channel/'+CID) == 'https://www.youtube.com/channel/'+CID


@pytest.mark.parametrize('display,value,precision',[('1.2M',1200000,'rounded_public_display'),('124M',124000000,'rounded_public_display'),
 ('243,292',243292,'published_integer_precision_unspecified'),('0',0,'published_integer_precision_unspecified')])
def test_instagram_preserves_public_rounding_and_original_display(display,value,precision):
    result=social.parse_instagram(instagram(display),IG)
    assert result['value']==value and result['display_value']==display
    assert result['precision']==precision and result['status']=='collected'


def test_instagram_login_page_wrong_identity_or_absent_counter_are_missing():
    for page in ['<title>Login • Instagram</title>',instagram(handle='other'),instagram(display='missing')]:
        result=social.parse_instagram(page,IG)
        assert result['value'] is None and result['collected_at'] is None


@pytest.mark.parametrize('count',[0,1234,74700000])
def test_tiktok_reads_only_requested_profile_followers(count):
    result=social.parse_tiktok(tiktok(count),TT)
    assert result['value']==count
    assert result['precision']=='published_integer_precision_unspecified'


@pytest.mark.parametrize('page',[tiktok(0,status=10222),tiktok(handle='other'),tiktok(-1),tiktok(True),tiktok('1.2M'),'login'])
def test_tiktok_errors_never_become_zero_followers(page):
    result=social.parse_tiktok(page,TT)
    assert result['value'] is None and result['status']=='unavailable'


def test_youtube_is_marked_rounded_even_for_an_integer_api_value():
    result=social.parse_youtube_api(youtube(),YT)
    assert result['value']==123000 and result['precision']=='rounded_down_3_significant_figures'
    by_id=social.parse_youtube_api(youtube(),f'https://www.youtube.com/channel/{CID}')
    assert by_id['value']==123000


@pytest.mark.parametrize('response',[youtube(hidden=True),youtube(count=None),youtube(count='-1'),youtube(handle='@other'),{'items':[]},{}])
def test_youtube_hidden_or_mismatched_channels_stay_unavailable(response):
    assert social.parse_youtube_api(response,YT)['value'] is None


@pytest.fixture
def public_cache(monkeypatch):
    values={}
    monkeypatch.setattr(social,'cache_get',lambda key:values.get(key))
    monkeypatch.setattr(social,'cache_set',lambda key,value,ttl:values.update({key:value}))
    monkeypatch.setattr(social.settings,'youtube_api_key','')
    return values


def mock_http(monkeypatch,handler):
    monkeypatch.setattr(social.httpx,'Client',lambda **kwargs:HTTP_CLIENT(transport=httpx.MockTransport(handler),**kwargs))


def test_youtube_missing_key_performs_no_request(monkeypatch,public_cache):
    mock_http(monkeypatch,lambda request:pytest.fail('No request without a configured key'))
    result=social.fetch_social_counter('youtube',YT)
    assert result['status']=='configuration_required' and result['error_code']=='YOUTUBE_API_KEY_REQUIRED'


def test_youtube_key_stays_in_headers_not_urls_or_records(monkeypatch,public_cache):
    monkeypatch.setattr(social.settings,'youtube_api_key','explicit-test-key-not-a-real-secret')
    def handle(request):
        assert request.url.host=='www.googleapis.com'
        assert request.headers['X-Goog-Api-Key']=='explicit-test-key-not-a-real-secret'
        assert 'key' not in request.url.params
        assert request.url.params['forHandle']=='@TestArtist'
        return httpx.Response(200,json=youtube())
    mock_http(monkeypatch,handle)
    result=social.fetch_social_counter('youtube',YT)
    assert result['value']==123000
    assert 'explicit-test-key' not in json.dumps(public_cache)


def test_public_http_collection_caches_actual_date(monkeypatch,public_cache):
    calls=[]
    def handle(request):
        calls.append(request)
        assert 'authorization' not in request.headers
        return httpx.Response(200,text=instagram(),headers={'Content-Type':'text/html'})
    mock_http(monkeypatch,handle)
    result=social.fetch_social_counter('instagram',IG)
    assert result['display_value']=='1.2M'
    assert social.fetch_social_counter('instagram',IG)==result
    assert len(calls)==1


@pytest.mark.parametrize('status',[302,401,403,404,429,500])
def test_failed_public_pages_are_not_retried_or_followed(monkeypatch,public_cache,status):
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(status,headers={'Location':'http://127.0.0.1/','Retry-After':'3600'})
    mock_http(monkeypatch,handle)
    assert social.fetch_social_counter('instagram',IG)['value'] is None
    assert social.fetch_social_counter('instagram',IG)['value'] is None
    assert len(calls)==1
    if status==429:
        assert social.fetch_social_counter('instagram','https://www.instagram.com/other/')['error_code']=='RATE_LIMITED'
        assert len(calls)==1


def test_snapshot_and_api_keep_social_precision_and_missing_states(monkeypatch,db_session,actors,client,headers):
    from app.db.models.discovery import DiscoveryArtist,DiscoverySnapshot
    from app.workers.discovery_pipeline import step_social
    artist=DiscoveryArtist(workspace_id=actors[1][0].id,canonical_name='Test',normalized_name='test',instagram_url=IG,tiktok_url=TT,youtube_url=YT)
    db_session.add(artist);db_session.flush()
    def collect(platform,url):
        return social.parse_instagram(instagram(),url) if platform=='instagram' else social.parse_tiktok(tiktok(0,status=10222),url) if platform=='tiktok' else social.observation('youtube',url,status='configuration_required',error_code='YOUTUBE_API_KEY_REQUIRED')
    monkeypatch.setattr(social,'fetch_social_counter',collect)
    observed=step_social(db_session,artist)
    actors[1][0].plan='premium';db_session.commit()
    snapshot=db_session.query(DiscoverySnapshot).filter(DiscoverySnapshot.source=='SOCIAL').one()
    assert snapshot.raw_payload['observations']['instagram']['precision']=='rounded_public_display'
    response=client.get(f'/api/v1/discovery/artist/{artist.id}',headers=headers())
    assert response.status_code==200,response.text
    data=response.json()
    assert data['instagram_followers']==1200000 and data['tiktok_followers'] is None
    assert data['youtube_subscribers'] is None
    assert data['social_observations']['instagram']['collected_at']==observed['instagram']['collected_at']
    assert data['social_observations']['youtube']['status']=='configuration_required'


def test_social_profile_edits_are_validated_scoped_and_gated(client,db_session,actors,headers):
    from app.db.models.discovery import DiscoveryArtist
    artist=DiscoveryArtist(workspace_id=actors[1][0].id,canonical_name='Test',normalized_name='test')
    db_session.add(artist);db_session.commit()
    route=f'/api/v1/discovery/artist/{artist.id}/social-profiles'
    assert client.patch(route,headers=headers(),json={'instagram_url':IG}).status_code==403
    for workspace in actors[1]:workspace.plan='premium'
    db_session.commit()
    assert client.patch(route,headers=headers(1),json={'instagram_url':IG}).status_code==404
    assert client.patch(route,headers=headers(3),json={'instagram_url':IG}).status_code==403
    assert client.patch(route,headers=headers(),json={'instagram_url':'http://127.0.0.1/'}).status_code==422
    response=client.patch(route,headers=headers(),json={'instagram_url':IG,'tiktok_url':TT,'youtube_url':YT})
    assert response.status_code==200,response.text
    assert response.json()=={'instagram':IG,'tiktok':TT,'youtube':YT}


def test_spotify_profile_links_are_explicit_and_host_validated():
    import base64
    from app.enrichment.providers.spotify_scraper import parse_spotify_artist_page
    aid='4tZwfgrHOc3mvqYlEYSvVi';uri='spotify:artist:'+aid
    state={'entities':{'items':{uri:{'uri':uri,'stats':{'monthlyListeners':1234},'profile':{'name':'Test','externalLinks':{'items':[
        {'url':'https://instagram.com/Test.Artist/?hl=en'},
        {'url':'https://instagram.com.evil.invalid/test'},
        {'url':'https://www.tiktok.com/@test.artist/video/1'}]}}}}}}
    encoded=base64.b64encode(json.dumps(state).encode()).decode()
    result=parse_spotify_artist_page(f'<script id="initialState">{encoded}</script>',aid)
    assert result['social_profiles']=={'instagram':IG}


def test_computation_uses_public_counters_preserves_zero_and_never_maps_deezer_fans(monkeypatch,db_session,actors,client,headers):
    from app.db.models.discovery import DiscoveryArtist,DiscoverySnapshot,DiscoveryEnrichmentJob,DiscoveryComputedMetrics
    from app.workers.discovery_pipeline import step_compute
    artist=DiscoveryArtist(workspace_id=actors[1][0].id,canonical_name='Test',normalized_name='test',instagram_url=IG,tiktok_url=TT,youtube_url=YT)
    db_session.add(artist);db_session.flush()
    job=DiscoveryEnrichmentJob(workspace_id=actors[1][0].id,artist_id=artist.id,input_type='NAME',input_value='Test')
    db_session.add_all([job,DiscoverySnapshot(artist_id=artist.id,source='SPOTIFY',status='OK',ttl_expires_at=datetime.utcnow()+timedelta(hours=12),raw_payload={'monthly_listeners':300,'deezer_fans':999999})])
    db_session.commit()
    def collect(platform,url):
        if platform=='instagram':return social.parse_instagram(instagram(),url)
        if platform=='tiktok':return social.parse_tiktok(tiktok(0),url)
        return social.observation(platform,url,status='configuration_required',error_code='YOUTUBE_API_KEY_REQUIRED')
    monkeypatch.setattr(social,'fetch_social_counter',collect)
    step_compute(db_session,job,False,True)
    metrics=db_session.query(DiscoveryComputedMetrics).filter(DiscoveryComputedMetrics.artist_id==artist.id).one()
    assert metrics.instagram_followers==1200000 and metrics.tiktok_followers==0
    assert metrics.youtube_subscribers is None and metrics.spotify_followers==0
    assert metrics.total_social_followers==1200000
    actors[1][0].plan='premium';db_session.commit()
    route=f'/api/v1/discovery/artist/{artist.id}'
    assert client.patch(route+'/social-profiles',headers=headers(),json={'instagram_url':'https://www.instagram.com/other/'}).status_code==200
    detail=client.get(route,headers=headers()).json()
    assert detail['instagram_followers'] is None
    assert detail['social_observations']['instagram']['error_code']=='PROFILE_CHANGED_REFRESH_REQUIRED'
    assert detail['tiktok_followers']==0
    assert detail['followers'] is None  # Never the total across other networks or Deezer fans.


def test_existing_third_party_observations_remain_labelled(monkeypatch,db_session,actors):
    from datetime import datetime
    from app.db.models.discovery import DiscoveryArtist,DiscoverySnapshot
    from app.workers.discovery_pipeline import step_social
    artist=DiscoveryArtist(workspace_id=actors[1][0].id,canonical_name='Test',normalized_name='test',viberate_url='https://www.viberate.com/artist/test/')
    db_session.add(artist);db_session.flush()
    legacy=DiscoverySnapshot(artist_id=artist.id,source='VIBERATE',status='OK',fetched_at=datetime.utcnow(),raw_payload={'social_stats':{'instagram_followers':42}})
    monkeypatch.setattr(social,'fetch_social_counter',lambda p,url:social.observation(p,None,error_code='NO_PROFILE_URL'))
    result=step_social(db_session,artist,legacy)
    assert result['instagram']['value']==42
    assert result['instagram']['precision']=='third_party_unspecified'
    assert result['instagram']['source_url']==artist.viberate_url
    assert result['youtube']['value'] is None


def test_publicly_returned_counter_is_separate_from_post_privacy():
    # Only the anonymous, successful profile counter is read; no posts are fetched.
    assert social.parse_tiktok(tiktok(1234,private=True),TT)['value']==1234


@pytest.mark.parametrize('failure',[httpx.ReadTimeout('test timeout'),httpx.ProxyError('test proxy denial')])
def test_network_failures_remain_unavailable_and_cached(monkeypatch,public_cache,failure):
    calls=[]
    def handle(request):
        calls.append(request)
        raise failure
    mock_http(monkeypatch,handle)
    result=social.fetch_social_counter('instagram',IG)
    assert result['error_code']=='NETWORK_OR_PROVIDER_UNAVAILABLE' and result['value'] is None
    assert social.fetch_social_counter('instagram',IG)==result
    assert len(calls)==1


def test_public_counter_page_size_is_bounded(monkeypatch,public_cache):
    mock_http(monkeypatch,lambda request:httpx.Response(200,text='x'*(social.MAX_BYTES+1),headers={'Content-Type':'text/html'}))
    assert social.fetch_social_counter('instagram',IG)['error_code']=='RESPONSE_TOO_LARGE'
