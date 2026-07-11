import authClient from './authClient.js';

export const authorizationHeaders = async (client = authClient) => {
  const token = String(await client.getAccessToken?.() || '').trim();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const withBearerAuthorization = async (options = {}, client = authClient) => {
  const headers = new Headers(options.headers || {});
  const authHeaders = await authorizationHeaders(client);

  if (authHeaders.Authorization) {
    headers.set('Authorization', authHeaders.Authorization);
  } else {
    headers.delete('Authorization');
  }

  return { ...options, headers };
};

export const authenticatedFetch = async (
  input,
  options = {},
  { client = authClient, fetchImpl = globalThis.fetch } = {},
) => {
  if (typeof fetchImpl !== 'function') {
    throw new Error('Fetch API is not available.');
  }

  return fetchImpl(input, await withBearerAuthorization(options, client));
};
