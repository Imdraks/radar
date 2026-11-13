import test from 'node:test';
import assert from 'node:assert/strict';
import {CONSENT_VERSION,readConsent,consentExpiresAt} from '../frontend/src/lib/consent.ts';
test('legacy/undated/malformed choices never authorize analytics',()=>{
 for(const raw of [null,'x','{}',JSON.stringify({analytics:'granted'}),JSON.stringify({version:CONSENT_VERSION,analytics:'granted',chosenAt:'invalid'})])assert.equal(readConsent(raw),null);
});
test('both grant and refusal expire after six calendar months',()=>{
 const chosenAt='2026-08-31T12:00:00.000Z';
 assert.equal(new Date(consentExpiresAt(chosenAt)).toISOString(),'2027-02-28T12:00:00.000Z');
 for(const analytics of ['granted','denied']){
  const raw=JSON.stringify({version:CONSENT_VERSION,chosenAt,analytics});
  assert.equal(readConsent(raw,Date.parse('2026-11-13T12:00:00Z')).analytics,analytics);
  assert.equal(readConsent(raw,Date.parse('2027-03-01T00:00:00Z')),null);
 }
});
test('a future consent cannot extend permission',()=>{
 assert.equal(readConsent(JSON.stringify({version:CONSENT_VERSION,chosenAt:'2030-01-01T00:00:00Z',analytics:'granted'}),Date.parse('2026-11-13')),null);
});
