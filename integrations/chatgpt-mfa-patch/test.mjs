import test from 'node:test';
import assert from 'node:assert/strict';
import { mfaLogin } from './mfa-login.mjs';

function fixture(methods) {
  const calls = [];
  const api = { raw: async (path, options) => {
    calls.push([path, options]);
    if (path === '/auth/login') return methods ? { requires_2fa: true, temp_token: 'explicit-test-challenge', methods } : { access_token: 'explicit-test-access', refresh_token: 'explicit-test-refresh' };
    if (path === '/auth/mfa/send') return { sent: true };
    if (path === '/auth/mfa/complete') return { access_token: 'explicit-test-access', refresh_token: 'explicit-test-refresh' };
    if (path === '/auth/me') return { id: 7 };
    if (path === '/workspaces') return { items: [{ id: 8 }] };
    assert.fail(path);
  } };
  return { api, calls };
}

test('TOTP challenge completed before obtaining user or workspace', async () => {
  const f = fixture(['totp', 'recovery']);
  await assert.rejects(mfaLogin(f.api, 'test@example.com', 'explicit-test-password'), { status: 401 });
  assert.equal(f.calls.length, 1);
  const result = await mfaLogin(f.api, 'test@example.com', 'explicit-test-password', '123456');
  assert.equal(result.user.id, 7);
  assert.equal(f.calls[1][1].body.method, 'totp');
  assert.equal(f.calls.filter(([path]) => path === '/auth/login').length, 1);
});

for (const channel of ['email', 'sms']) test(`${channel} sent once then bound challenge consumed`, async () => {
  const f = fixture([channel, 'recovery']);
  for (let repeat = 0; repeat < 2; repeat++) await assert.rejects(mfaLogin(f.api, 'test@example.com', 'explicit-test-password'), { status: 401 });
  assert.equal(f.calls.filter(([path]) => path === '/auth/mfa/send').length, 1);
  const result = await mfaLogin(f.api, 'test@example.com', 'explicit-test-password', '123456');
  assert.equal(result.workspaces[0].id, 8);
  assert.equal(f.calls.find(([path]) => path === '/auth/mfa/complete')[1].body.method, channel);
});

test('recovery works without an SMS delivery when provider is unavailable', async () => {
  const f = fixture(['sms', 'recovery']);
  await mfaLogin(f.api, 'test@example.com', 'explicit-test-password', 'ABCD-1234-FFFF-EEEE');
  assert.equal(f.calls.filter(([path]) => path === '/auth/mfa/send').length, 0);
  assert.equal(f.calls[1][1].body.method, 'recovery');
});

test('provider failure is not mistaken for a delivered code or authenticated grant', async () => {
  const f = fixture(['email']);
  const original = f.api.raw;
  f.api.raw = async (path, options) => {
    if (path === '/auth/mfa/send') throw Object.assign(new Error('service unavailable'), { status: 503 });
    return original(path, options);
  };
  await assert.rejects(mfaLogin(f.api, 'test@example.com', 'explicit-test-password'), { status: 503 });
  assert.equal(f.calls.filter(([path]) => path === '/auth/me').length, 0);
});

test('a changed password does not reuse another first-factor proof', async () => {
  const f = fixture(['totp']);
  await assert.rejects(mfaLogin(f.api, 'test@example.com', 'explicit-test-password'), { status: 401 });
  await mfaLogin(f.api, 'test@example.com', 'another-explicit-test-password', '123456');
  assert.equal(f.calls.filter(([path]) => path === '/auth/login').length, 2);
});

test('unprotected account keeps original login return shape', async () => {
  const f = fixture(null);
  const result = await mfaLogin(f.api, 'test@example.com', 'explicit-test-password');
  assert.deepEqual(result.workspaces, [{ id: 8 }]);
  assert.equal(result.tokens.access_token, 'explicit-test-access');
});
