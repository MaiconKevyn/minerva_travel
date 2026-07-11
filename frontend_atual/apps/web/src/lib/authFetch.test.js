import assert from 'node:assert/strict';
import test from 'node:test';

import {
  authenticatedFetch,
  authorizationHeaders,
  withBearerAuthorization,
} from './authFetch.js';

const clientWithToken = (token) => ({
  getAccessToken: async () => token,
});

test('authorizationHeaders builds a Bearer header from authClient access token', async () => {
  assert.deepEqual(
    await authorizationHeaders(clientWithToken('session-token')),
    { Authorization: 'Bearer session-token' },
  );
  assert.deepEqual(await authorizationHeaders(clientWithToken(null)), {});
});

test('withBearerAuthorization preserves request headers and replaces stale authorization', async () => {
  const originalHeaders = new Headers({
    Accept: 'application/json',
    Authorization: 'Basic stale-credential',
    'X-Request-Source': 'test',
  });
  const options = { method: 'POST', headers: originalHeaders };
  const protectedOptions = await withBearerAuthorization(
    options,
    clientWithToken('fresh-token'),
  );

  assert.equal(protectedOptions.method, 'POST');
  assert.equal(protectedOptions.headers.get('Accept'), 'application/json');
  assert.equal(protectedOptions.headers.get('X-Request-Source'), 'test');
  assert.equal(protectedOptions.headers.get('Authorization'), 'Bearer fresh-token');
  assert.equal(originalHeaders.get('Authorization'), 'Basic stale-credential');
});

test('withBearerAuthorization removes caller authorization when authClient has no session', async () => {
  const options = await withBearerAuthorization(
    { headers: { Authorization: 'Bearer stale-token' } },
    clientWithToken(null),
  );

  assert.equal(options.headers.has('Authorization'), false);
});

test('authenticatedFetch sends FormData with Bearer auth and leaves Content-Type to the browser', async () => {
  const formData = new FormData();
  formData.append('family_name', 'Silva');
  const response = { ok: true };
  const calls = [];

  const result = await authenticatedFetch(
    'https://api.example.com/generate',
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body: formData,
    },
    {
      client: clientWithToken('upload-token'),
      fetchImpl: async (...args) => {
        calls.push(args);
        return response;
      },
    },
  );

  assert.equal(result, response);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'https://api.example.com/generate');
  assert.equal(calls[0][1].body, formData);
  assert.equal(calls[0][1].headers.get('Authorization'), 'Bearer upload-token');
  assert.equal(calls[0][1].headers.get('Accept'), 'application/json');
  assert.equal(calls[0][1].headers.has('Content-Type'), false);
});
