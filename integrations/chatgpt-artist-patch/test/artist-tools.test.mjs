import test from 'node:test';
import assert from 'node:assert/strict';
import { z } from 'zod/v4';
import { artistInput, registerArtistTools } from '../artist-tools.mjs';

const first = '11111111-1111-4111-8111-111111111111';
const second = '22222222-2222-4222-8222-222222222222';
const jobId = '33333333-3333-4333-8333-333333333333';

function fixture(request, publicSearch = async () => ({ source: 'Deezer', artists: [] })) {
  const tools = new Map();
  const calls = [];
  const bridge = {
    request: async (...args) => { calls.push(args); return request(...args); },
    api: { searchPublicArtists: publicSearch },
  };
  registerArtistTools((name, title, description, schema, action, options) => {
    assert.ok(!tools.has(name));
    tools.set(name, { options, call: args => action(z.object(schema).strict().parse(args)) });
  }, bridge, 'fixed-grant');
  return { tools, calls, call: (name, args) => tools.get(name).call(args) };
}

test('four named tools, writing only through the existing write consent gate', () => {
  const { tools } = fixture(() => {});
  assert.deepEqual([...tools.keys()], ['search_artists', 'get_artist_profile', 'save_artist', 'compare_artists']);
  for (const [name, tool] of tools) assert.equal(tool.options.read, name !== 'save_artist');
  assert.equal(tools.get('save_artist').options.idempotent, false);
});

test('name search preserves workspace candidates and labels real provider data', async () => {
  const f = fixture(async (grant, path) => {
    assert.equal(grant, 'fixed-grant');
    assert.equal(path, '/artists/autocomplete?q=SCH&limit=10');
    return { items: [{ artist_id: first, display_name: 'SCH' }] };
  }, async (query, limit, index) => {
    assert.deepEqual([query, limit, index], ['SCH', 10, 0]);
    return { source: 'Deezer', artists: [{ name: 'SCH', deezer_fans: 123 }] };
  });
  const result = await f.call('search_artists', { query: ' SCH ' });
  assert.equal(result.workspace_results[0].artist_id, first);
  assert.equal(result.public_results.status, 'available');
  assert.equal(result.public_results.artists[0].deezer_fans, 123);
  assert.equal(result.public_results.artists[0].monthly_listeners, undefined);
});

test('external failure is explicitly partial, never synthetic statistics', async () => {
  const f = fixture(async () => ({ items: [] }), async () => { throw new Error('secret upstream body'); });
  const result = await f.call('search_artists', { query: 'SCH' });
  assert.equal(result.public_results.status, 'unavailable');
  assert.deepEqual(result.public_results.artists, []);
  assert.ok(!JSON.stringify(result).includes('secret'));
});

test('backend workspace denial is not masked by public search', async () => {
  let publicCalled = false;
  const f = fixture(async () => { throw Object.assign(new Error('forbidden'), { status: 403 }); },
    async () => { publicCalled = true; });
  await assert.rejects(f.call('search_artists', { query: 'SCH' }), { status: 403 });
  assert.equal(publicCalled, false);
});

test('URL resolution is read-only and strips tracking parameters', async () => {
  const input = 'https://open.spotify.com/artist/0123456789012345678901';
  const f = fixture(async (grant, path, options) => {
    assert.equal(path, '/artists/search');
    assert.deepEqual(options, { method: 'POST', body: { input_type: 'SPOTIFY_URL', input_value: input } });
    return { status: 'RESOLVED' };
  });
  const result = await f.call('search_artists', { query: `${input}?si=tracking` });
  assert.equal(result.status, 'RESOLVED');
  assert.equal(f.calls.length, 1);
});

test('unsupported, deceptive and credential-bearing URLs are rejected', () => {
  for (const query of [
    'https://localhost/artist/name', 'http://viberate.com/artist/sch',
    'https://viberate.com.evil.test/artist/sch', 'https://name:password@viberate.com/artist/sch',
    'https://open.spotify.com:444/artist/0123456789012345678901',
    'https://open.spotify.com/artist/0123456789012345678901/more',
    'https://viberate.com/artist/../../admin', 'file:///etc/passwd',
  ]) assert.throws(() => artistInput(query), { status: 422 });
});

test('profile keeps provenance and does not invent an absent score', async () => {
  const evidence = [{ source: 'SPOTIFY', collected_at: '2026-11-16T10:00:00Z', status: 'PARTIAL' }];
  const f = fixture(async (grant, path) => {
    assert.equal(path, `/discovery/artist/${first}`);
    return { id: first, score: 0, data_quality: null, monthly_listeners: null, evidence };
  });
  const result = await f.call('get_artist_profile', { artist_id: first });
  assert.equal(result.artist.score, null);
  assert.equal(result.artist.monthly_listeners, null);
  assert.deepEqual(result.artist.evidence, evidence);
});

test('profile requires exactly one UUID; no request is sent for bad input', async () => {
  const f = fixture(() => assert.fail('No backend request expected'));
  await assert.rejects(f.call('get_artist_profile', {}), { status: 422 });
  await assert.rejects(f.call('get_artist_profile', { artist_id: first, job_id: jobId }), { status: 422 });
  assert.throws(() => f.call('get_artist_profile', { artist_id: '../secrets' }));
  assert.throws(() => f.call('save_artist', { query: 'SCH', workspace_id: 999 }));
  assert.equal(f.calls.length, 0);
});

test('pending jobs never claim saved statistics; provider error text is withheld', async () => {
  for (const status of ['QUEUED', 'RUNNING', 'FAILED']) {
    const f = fixture(async () => ({ id: jobId, artist_id: first, status, error_code: 'PROVIDER_ERROR', error_message: 'password=private' }));
    const result = await f.call('get_artist_profile', { job_id: jobId });
    assert.equal(result.artist, undefined);
    assert.equal(result.job.error_message, undefined);
    assert.equal(result.job.status, status);
    assert.equal(f.calls.length, 1);
  }
});

test('partial/completed jobs fetch the scoped saved profile', async () => {
  for (const status of ['PARTIAL', 'DONE']) {
    const f = fixture(async (grant, path) => path.startsWith('/artists/jobs/')
      ? { id: jobId, artist_id: first, status }
      : { id: first, data_quality: 'LOW', score: 12, missing_data: ['monthly_listeners'] });
    const result = await f.call('get_artist_profile', { job_id: jobId });
    assert.equal(result.job.status, status);
    assert.equal(result.artist.score, 12);
    assert.deepEqual(result.artist.missing_data, ['monthly_listeners']);
    assert.equal(f.calls.length, 2);
  }
});

test('existing artist does not launch a second enrichment', async () => {
  const f = fixture(async () => ({ status: 'FOUND', artist_id: first }));
  assert.deepEqual(await f.call('save_artist', { query: 'SCH' }), { status: 'ALREADY_SAVED', artist_id: first });
  assert.equal(f.calls.length, 1);
});

test('ambiguous resolution asks for selection without launching a job', async () => {
  const f = fixture(async () => ({ status: 'NEED_SELECTION', candidates: [{ display_name: 'One' }, { display_name: 'Two' }] }));
  assert.equal((await f.call('save_artist', { query: 'Artist' })).status, 'NEED_SELECTION');
  assert.equal(f.calls.length, 1);
});

test('save uses server-resolved identity and returns a pending job', async () => {
  const identity = { display_name: 'SCH', input_type: 'NAME' };
  const f = fixture(async (grant, path, options) => {
    if (path === '/artists/search') return { status: 'RESOLVED', resolved: identity };
    assert.equal(path, '/artists/analyze');
    assert.deepEqual(options, { method: 'POST', body: { resolved: identity } });
    return { status: 'JOB_CREATED', job_id: jobId };
  });
  const result = await f.call('save_artist', { query: 'SCH' });
  assert.equal(result.pending, true);
  assert.equal(result.job_id, jobId);
  assert.equal(result.artist_id, undefined);
});

test('dispatch failure is an error rather than a completed save', async () => {
  const f = fixture(async (grant, path) => {
    if (path === '/artists/search') return { status: 'RESOLVED', resolved: { display_name: 'SCH', input_type: 'NAME' } };
    throw Object.assign(new Error('Radar ne peut pas traiter cette demande.'), { status: 503 });
  });
  await assert.rejects(f.call('save_artist', { query: 'SCH' }), { status: 503 });
});

test('comparison requires the backend comparison entitlement', async () => {
  const f = fixture(async (grant, path) => {
    assert.equal(path, '/subscription/features/comparison');
    return { available: false };
  });
  await assert.rejects(f.call('compare_artists', { artist_ids: [first, second] }), { status: 403 });
  assert.equal(f.calls.length, 1);
});

test('comparison preserves missing values and tenant errors; no partial data leaks', async () => {
  const f = fixture(async (grant, path) => {
    if (path.startsWith('/subscription/')) return { available: true };
    if (path.endsWith(second)) throw Object.assign(new Error('Not found in workspace'), { status: 404 });
    return { id: first, data_quality: 'LOW', monthly_listeners: null };
  });
  await assert.rejects(f.call('compare_artists', { artist_ids: [first, second] }), { status: 404 });
  assert.ok(f.calls.every(([grant]) => grant === 'fixed-grant'));
  assert.ok(f.calls.every(([, , options]) => options === undefined));
});

test('comparison rejects duplicates and bounds input before any backend reads', async () => {
  const f = fixture(() => assert.fail('No backend request expected'));
  await assert.rejects(f.call('compare_artists', { artist_ids: [first, first] }), { status: 422 });
  assert.throws(() => f.call('compare_artists', { artist_ids: [first] }));
  assert.throws(() => f.call('compare_artists', { artist_ids: Array(6).fill(first) }));
});
