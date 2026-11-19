import { api } from './api';

function decode(value: string): ArrayBuffer {
  const text = value.replace(/-/g, '+').replace(/_/g, '/');
  return Uint8Array.from(atob(text), char => char.charCodeAt(0)).buffer;
}
function encode(value: ArrayBuffer) {
  return btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function available() {
  if (!window.isSecureContext || !window.PublicKeyCredential || !navigator.credentials) throw new Error('Les clés d’accès nécessitent un navigateur compatible et une connexion HTTPS.');
}
function serialize(credential: PublicKeyCredential) {
  const response = credential.response;
  const common = { id: credential.id, rawId: encode(credential.rawId), type: credential.type, clientExtensionResults: credential.getClientExtensionResults() };
  if (response instanceof AuthenticatorAttestationResponse) return { ...common, response: { clientDataJSON: encode(response.clientDataJSON), attestationObject: encode(response.attestationObject), transports: response.getTransports?.() || [] } };
  const assertion = response as AuthenticatorAssertionResponse;
  return { ...common, response: { clientDataJSON: encode(assertion.clientDataJSON), authenticatorData: encode(assertion.authenticatorData), signature: encode(assertion.signature), userHandle: assertion.userHandle ? encode(assertion.userHandle) : null } };
}
export async function registerPasskey(managementToken: string, name: string) {
  available();
  const { data } = await api.post('/auth/passkeys/register/options', { management_token: managementToken });
  const options = data.publicKey;
  const credential = await navigator.credentials.create({ publicKey: { ...options, challenge: decode(options.challenge), user: { ...options.user, id: decode(options.user.id) }, excludeCredentials: (options.excludeCredentials || []).map((key: { id: string }) => ({ ...key, id: decode(key.id) })) } }) as PublicKeyCredential | null;
  if (!credential) throw new Error('Ajout de la clé annulé.');
  return (await api.post('/auth/passkeys/register/complete', { challenge_id: data.challenge_id, name, credential: serialize(credential) })).data;
}
export async function authenticatePasskey(challengeToken: string, trustDevice = false) {
  available();
  const { data } = await api.post('/auth/passkeys/authenticate/options', { challenge_token: challengeToken });
  const options = data.publicKey;
  const credential = await navigator.credentials.get({ publicKey: { ...options, challenge: decode(options.challenge), allowCredentials: (options.allowCredentials || []).map((key: { id: string }) => ({ ...key, id: decode(key.id) })) } }) as PublicKeyCredential | null;
  if (!credential) throw new Error('Vérification annulée.');
  return (await api.post('/auth/passkeys/authenticate/complete', { challenge_token: challengeToken, challenge_id: data.challenge_id, trust_device: trustDevice, credential: serialize(credential) })).data;
}
export async function verifyReauthentication(token: string, method: string, code: string) {
  return method === 'passkey' ? authenticatePasskey(token) : (await api.post('/auth/mfa/reauth/complete', { challenge_token: token, method, code })).data;
}
