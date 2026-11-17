import { z } from 'zod/v4';

const querySchema = z.string().trim().min(2).max(200);
const uuid = z.string().uuid();
const failure = (status, message) => Object.assign(new Error(message), { status });

export const artistTools = [
  { name: 'search_artists', title: 'Rechercher des artistes', family: 'artists', read: true,
    description: 'Cherchez par nom dans le workspace et le catalogue public Deezer, ou résolvez une URL Spotify/Viberate. Les candidats publics ne sont pas encore enregistrés dans Radar. Les fans Deezer ne sont pas des auditeurs mensuels Spotify.' },
  { name: 'get_artist_profile', title: 'Fiche artiste et suivi de collecte', family: 'artists', read: true,
    description: 'Consultez une fiche par artist_id UUID, ou suivez un enrichissement par job_id UUID. Fournissez exactement un de ces identifiants. Sources, dates, estimations et données manquantes restent explicites.' },
  { name: 'save_artist', title: 'Enregistrer et enrichir un artiste', family: 'artists', read: false,
    description: 'Sur demande de l’utilisateur, enregistrez/enrichissez un artiste par nom ou URL Spotify/Viberate. Exige radar:write. JOB_CREATED et ALREADY_RUNNING sont des travaux en attente : suivez job_id avec get_artist_profile avant d’annoncer un enregistrement terminé.' },
  { name: 'compare_artists', title: 'Comparer des artistes enregistrés', family: 'artists', read: true,
    description: 'Comparez 2 à 5 artistes du workspace à partir de leurs UUID, sans créer de sélection. Les mesures absentes restent nulles et les estimations ne sont pas des certitudes. Aucun classement ou pourcentage de réussite n’est inventé.' },
];

export const artistToolNames = new Set(artistTools.map(tool => tool.name));

export function artistInput(query) {
  if (/^https?:\/\//i.test(query) || query.startsWith('www.') || query.includes('://')) {
    let url;
    try { url = new URL(query); } catch { throw failure(422, 'URL artiste invalide.'); }
    if (url.protocol !== 'https:' || url.username || url.password || url.port) {
      throw failure(422, 'Utilisez une URL HTTPS Spotify ou Viberate sans identifiants.');
    }
    const spotify = url.hostname === 'open.spotify.com' && /^\/artist\/[A-Za-z0-9]{22}\/?$/.test(url.pathname);
    const viberate = ['viberate.com', 'www.viberate.com'].includes(url.hostname) && /^\/artist\/[A-Za-z0-9_-]+\/?$/.test(url.pathname);
    if (!spotify && !viberate) throw failure(422, 'Seules les URL de fiches artistes Spotify et Viberate sont prises en charge.');
    return { input_type: spotify ? 'SPOTIFY_URL' : 'VIBERATE_URL', input_value: `${url.origin}${url.pathname}` };
  }
  return { input_type: 'NAME', input_value: query };
}

function checkedUUID(value) {
  const parsed = uuid.safeParse(value);
  if (!parsed.success) throw failure(502, 'Radar a renvoyé un identifiant artiste invalide.');
  return parsed.data;
}

async function profile(bridge, grantId, artistId) {
  const detail = await bridge.request(grantId, `/discovery/artist/${checkedUUID(artistId)}`);
  // Discovery's historical response defaults score to 0 even without metrics.
  // Its data_quality is populated only when computed metrics exist.
  return { ...detail, score: detail.data_quality == null ? null : detail.score };
}

export function registerArtistTools(register, bridge, grantId) {
  const add = (name, schema, action, options = {}) => {
    const tool = artistTools.find(item => item.name === name);
    register(name, tool.title, tool.description, schema, action,
      { read: tool.read, destructive: false, external: true, ...options });
  };

  add('search_artists', {
    query: querySchema,
    limit: z.number().int().min(1).max(20).default(10),
  }, async ({ query, limit }) => {
    const input = artistInput(query);
    if (input.input_type !== 'NAME') {
      const result = await bridge.request(grantId, '/artists/search', { method: 'POST', body: input });
      return { ...result, input, note: 'RESOLVED valide la forme de l’URL ; ce statut ne prouve pas que le fournisseur a vérifié l’artiste.' };
    }
    const local = await bridge.request(grantId, `/artists/autocomplete?${new URLSearchParams({ q: query, limit: String(limit) })}`);
    let publicResult;
    try {
      publicResult = { status: 'available', ...await bridge.api.searchPublicArtists(query, limit, 0) };
    } catch {
      publicResult = { status: 'unavailable', source: 'Deezer', artists: [],
        message: 'Catalogue public indisponible ; seuls les résultats du workspace sont disponibles.' };
    }
    return { query, workspace_results: local.items, public_results: publicResult };
  });

  add('get_artist_profile', { artist_id: uuid.optional(), job_id: uuid.optional() }, async ({ artist_id, job_id }) => {
    if (Boolean(artist_id) === Boolean(job_id)) throw failure(422, 'Fournissez artist_id ou job_id, exclusivement.');
    if (artist_id) return { artist: await profile(bridge, grantId, artist_id) };
    const result = await bridge.request(grantId, `/artists/jobs/${job_id}`);
    const job = Object.fromEntries(['id', 'artist_id', 'artist_name', 'status', 'current_step',
      'progress_pct', 'error_code', 'created_at', 'completed_at'].filter(key => result[key] !== undefined).map(key => [key, result[key]]));
    // Do not relay raw provider/DB error_message or mistake a partial job for success.
    return { job, ...(['DONE', 'PARTIAL'].includes(job.status) && job.artist_id
      ? { artist: await profile(bridge, grantId, job.artist_id) } : {}) };
  });

  add('save_artist', { query: querySchema }, async ({ query }) => {
    const input = artistInput(query);
    const resolved = await bridge.request(grantId, '/artists/search', { method: 'POST', body: input });
    if (resolved.status === 'FOUND' && resolved.artist_id) {
      return { status: 'ALREADY_SAVED', artist_id: checkedUUID(resolved.artist_id) };
    }
    if (resolved.status === 'NEED_SELECTION') {
      return { status: 'NEED_SELECTION', candidates: resolved.candidates ?? [],
        message: 'Plusieurs artistes correspondent. Demandez une URL Spotify/Viberate précise avant de poursuivre.' };
    }
    if (resolved.status !== 'RESOLVED' || !resolved.resolved) {
      throw failure(422, 'Radar n’a pas pu résoudre cet artiste. Précisez son nom ou son URL.');
    }
    // Preserve the server-resolved identity; never forward arbitrary assistant fields.
    const result = await bridge.request(grantId, '/artists/analyze', {
      method: 'POST', body: { resolved: resolved.resolved },
    });
    return { ...result, pending: ['JOB_CREATED', 'ALREADY_RUNNING'].includes(result.status),
      next_step: result.job_id ? 'Appelez get_artist_profile avec job_id pour suivre le résultat réel.' : null };
  }, { idempotent: false });

  add('compare_artists', {
    artist_ids: z.array(uuid).min(2).max(5),
  }, async ({ artist_ids }) => {
    if (new Set(artist_ids).size !== artist_ids.length) throw failure(422, 'Les artistes à comparer doivent être distincts.');
    const feature = await bridge.request(grantId, '/subscription/features/comparison');
    if (feature.available !== true) throw failure(403, 'La comparaison n’est pas activée dans votre offre Radar.');
    // Reads remain behind Radar's grant workspace, tenant and subscription checks.
    // Sequential and bounded: no unbounded fan-out to providers or workers.
    const artists = [];
    for (const artistId of artist_ids) artists.push(await profile(bridge, grantId, artistId));
    return { artists, method: 'Comparaison des observations enregistrées, sans classement automatique.' };
  });
}
