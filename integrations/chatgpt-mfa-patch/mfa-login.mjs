import { createHmac, randomBytes } from 'node:crypto';

// No raw password cache. Challenges are first-factor proofs, short-lived and
// one-use on Radar's server. All grants continue through the original OAuth UI.
const states = new WeakMap();
const denied = message => Object.assign(new Error(message), { status: 401 });

export async function mfaLogin(api, email, password, suppliedCode) {
  let state = states.get(api);
  if (!state) { state = { key: randomBytes(32), pending: new Map() }; states.set(api, state); }
  const now = Date.now();
  for (const [key, entry] of state.pending) if (entry.expires <= now) state.pending.delete(key);
  const identity = createHmac('sha256', state.key).update(JSON.stringify([email, password])).digest('hex');
  let entry = state.pending.get(identity);
  const code = (suppliedCode || '').trim();
  let tokens;
  if (!entry) {
    tokens = await api.raw('/auth/login', { method: 'POST', body: { email, password } });
    if (tokens.requires_2fa) {
      if (!tokens.temp_token || !Array.isArray(tokens.methods)) throw denied('Mettez à jour Radar pour terminer la vérification de sécurité.');
      entry = { token: tokens.temp_token, methods: tokens.methods, expires: now + 270000, sent: false };
      if (state.pending.size >= 1000) state.pending.delete(state.pending.keys().next().value);
      state.pending.set(identity, entry);
    }
  }
  if (entry) {
    const normalized = code.replace(/[ -]/g, '');
    const recovery = normalized.length >= 8 && /^[A-Za-z0-9]+$/.test(normalized);
    const preferred = entry.methods.includes('totp') ? 'totp' : entry.methods.find(method => ['email', 'sms'].includes(method));
    if (code && (recovery || preferred === 'totp' || entry.sent)) {
      try {
        tokens = await api.raw('/auth/mfa/complete', { method: 'POST', body: {
          challenge_token: entry.token, method: recovery ? 'recovery' : preferred, code,
        } });
      } catch (error) {
        if (error.status === 429) state.pending.delete(identity);
        throw error;
      }
      state.pending.delete(identity);
    } else {
      if (preferred === 'email' || preferred === 'sms') {
        if (!entry.sent) {
          try { await api.raw('/auth/mfa/send', { method: 'POST', body: { challenge_token: entry.token, method: preferred } }); }
          catch (error) { state.pending.delete(identity); throw error; }
          entry.sent = true;
        }
        throw denied(`Un code a été demandé ${preferred === 'email' ? 'par e-mail' : 'par SMS'}. Saisissez-le dans le champ de double authentification, ou utilisez un code de secours.`);
      }
      throw denied('Saisissez le code de votre application d’authentification ou un code de secours.');
    }
  }
  if (!tokens?.access_token || !tokens.refresh_token) throw denied('La vérification doit être terminée avant de connecter Radar.');
  const user = await api.raw('/auth/me', { token: tokens.access_token });
  const workspaces = await api.raw('/workspaces', { token: tokens.access_token });
  return { tokens, user, workspaces: workspaces.items || [] };
}
