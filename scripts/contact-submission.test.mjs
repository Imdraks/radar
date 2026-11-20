import { test } from 'node:test';
import assert from 'node:assert/strict';
import { submitContactMessage } from '../frontend/src/lib/contact.ts';

const body = {name: 'TEST contact', email: 'test@example.com', message: 'TEST message'};
function reply(t, response) {
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/v1/contact');
    assert.deepEqual(options.headers, {'Content-Type':'application/json'});
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), body);
    assert.ok(options.signal instanceof AbortSignal);
    return response;
  };
  t.after(() => { globalThis.fetch = original; });
}

test('a public, same-origin request requires a real success acknowledgement', async t => {
  reply(t, Response.json({status:'ok'}));
  await submitContactMessage(body);
});
for (const [label, response] of [
  ['missing acknowledgement', Response.json({})],
  ['non-JSON proxy response', new Response('<html>Proxy error</html>', {status:502})],
]) test(label + ' never becomes success', async t => {
  reply(t, response);
  await assert.rejects(submitContactMessage(body), /temporairement indisponible/);
});
test('a known opaque reference is shown without the provider detail', async t => {
  reply(t, Response.json({detail:{code:'CONTACT_UNAVAILABLE',message:'SECRET',reference:'abcdef123456'}},{status:503}));
  await assert.rejects(submitContactMessage(body), error => error.message.includes('abcdef123456') && !error.message.includes('SECRET'));
});
test('untrusted references and provider payloads are never reflected', async t => {
  reply(t, Response.json({detail:{code:'CONTACT_UNAVAILABLE',message:'SECRET',reference:'<script>SECRET</script>'}},{status:503}));
  await assert.rejects(submitContactMessage(body), error => !error.message.includes('SECRET'));
});
for (const [status, pattern] of [[422,/Vérifiez le format/],[429,/Trop de tentatives/]]) test('HTTP '+status+' has an actionable message', async t => {
  reply(t, Response.json({detail:'SECRET'}, {status}));
  await assert.rejects(submitContactMessage(body), pattern);
});
test('network errors keep a safe message and never expose the underlying error', async t => {
  const original=globalThis.fetch;
  globalThis.fetch=async () => {throw new Error('SECRET transport error');};
  t.after(() => {globalThis.fetch=original;});
  await assert.rejects(submitContactMessage(body), error => error.message.includes('connexion') && !error.message.includes('SECRET'));
});
