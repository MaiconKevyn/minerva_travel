import assert from 'node:assert/strict';
import test from 'node:test';

import { createAuthClient, createMemoryStorage } from './authClient.js';

test('createAuthClient uses local auth when no Supabase configuration is provided', async () => {
  const storage = createMemoryStorage();
  const authClient = createAuthClient({ storage });
  const changes = [];

  const unsubscribe = authClient.subscribe((user) => {
    changes.push(user);
  });

  assert.equal(authClient.isValid, false);
  assert.equal(authClient.model, null);

  const signup = await authClient.signup('mae@example.com', 'Senha123', 'Mae');

  assert.deepEqual(signup, { success: true });
  assert.equal(authClient.isValid, false);
  assert.equal(storage.getItem('minerva_local_users').includes('Senha123'), false);

  const login = await authClient.login('mae@example.com', 'Senha123');

  assert.equal(login.success, true);
  assert.equal(authClient.isValid, true);
  assert.equal(authClient.model.email, 'mae@example.com');
  assert.equal(authClient.model.name, 'Mae');
  assert.equal(changes.at(-1).email, 'mae@example.com');

  authClient.logout();

  assert.equal(authClient.isValid, false);
  assert.equal(authClient.model, null);
  assert.equal(changes.at(-1), null);

  unsubscribe();
});

test('local auth rejects an unknown user', async () => {
  const storage = createMemoryStorage();
  const authClient = createAuthClient({ pocketBaseUrl: '', storage });

  const login = await authClient.login('mae@example.com', 'Senha123');

  assert.equal(login.success, false);
  assert.match(login.error, /credenciais/i);
  assert.equal(authClient.isValid, false);
});

test('createAuthClient uses Supabase auth when Supabase variables are configured', async () => {
  const calls = [];
  const signedInUser = {
    id: 'user-123',
    email: 'mae@example.com',
    user_metadata: { name: 'Mae' },
  };
  const supabaseClient = {
    auth: {
      getSession: async () => ({
        data: { session: null },
        error: null,
      }),
      onAuthStateChange: (listener) => {
        calls.push(['onAuthStateChange']);
        supabaseClient.emitAuthChange = listener;

        return {
          data: {
            subscription: {
              unsubscribe: () => calls.push(['unsubscribe']),
            },
          },
        };
      },
      signInWithPassword: async (credentials) => {
        calls.push(['signInWithPassword', credentials]);

        return {
          data: {
            session: { user: signedInUser },
            user: signedInUser,
          },
          error: null,
        };
      },
      signUp: async (payload) => {
        calls.push(['signUp', payload]);

        return {
          data: { user: signedInUser },
          error: null,
        };
      },
      signOut: async () => {
        calls.push(['signOut']);

        return { error: null };
      },
      resetPasswordForEmail: async (email, options) => {
        calls.push(['resetPasswordForEmail', email, options]);

        return { data: {}, error: null };
      },
      updateUser: async (attributes) => {
        calls.push(['updateUser', attributes]);

        return { data: { user: signedInUser }, error: null };
      },
    },
  };
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: (url, key) => {
      calls.push(['createSupabaseClient', url, key]);
      return supabaseClient;
    },
  });
  const changes = [];
  const unsubscribe = authClient.subscribe((user) => {
    changes.push(user);
  });

  await authClient.initialize();

  assert.deepEqual(calls[0], [
    'createSupabaseClient',
    'https://project.supabase.co',
    'sb_publishable_test',
  ]);
  assert.equal(authClient.isValid, false);

  const signup = await authClient.signup('mae@example.com', 'Senha123', 'Mae');
  const login = await authClient.login('mae@example.com', 'Senha123');

  assert.equal(signup.success, true);
  assert.equal(login.success, true);
  assert.equal(authClient.isValid, true);
  assert.equal(authClient.model.email, 'mae@example.com');
  assert.equal(authClient.model.name, 'Mae');
  assert.deepEqual(calls.find((call) => call[0] === 'signUp')[1], {
    email: 'mae@example.com',
    password: 'Senha123',
    options: { data: { name: 'Mae' } },
  });
  assert.deepEqual(calls.find((call) => call[0] === 'signInWithPassword')[1], {
    email: 'mae@example.com',
    password: 'Senha123',
  });

  await authClient.logout();

  assert.equal(authClient.isValid, false);
  assert.equal(authClient.model, null);
  assert.equal(changes.at(-1), null);

  unsubscribe();
  assert.equal(calls.some((call) => call[0] === 'unsubscribe'), true);
});

test('Supabase auth sends password reset email with redirect URL', async () => {
  const calls = [];
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        resetPasswordForEmail: async (email, options) => {
          calls.push([email, options]);

          return { data: {}, error: null };
        },
      },
    }),
  });

  const result = await authClient.requestPasswordReset(
    'mae@example.com',
    'https://example.com/reset-password',
  );

  assert.equal(result.success, true);
  assert.deepEqual(calls, [
    [
      'mae@example.com',
      { redirectTo: 'https://example.com/reset-password' },
    ],
  ]);
});

test('Supabase auth updates password after recovery redirect', async () => {
  const calls = [];
  const signedInUser = {
    id: 'user-123',
    email: 'mae@example.com',
    user_metadata: { name: 'Mae' },
  };
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => ({ data: { session: { user: signedInUser } }, error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        updateUser: async (attributes) => {
          calls.push(attributes);

          return { data: { user: signedInUser }, error: null };
        },
      },
    }),
  });

  const result = await authClient.updatePassword('NovaSenha123');

  assert.equal(result.success, true);
  assert.deepEqual(calls, [{ password: 'NovaSenha123' }]);
});

test('Supabase auth prepares password recovery from a code redirect', async () => {
  const calls = [];
  const signedInUser = {
    id: 'user-123',
    email: 'mae@example.com',
    user_metadata: { name: 'Mae' },
  };
  const recoverySession = { user: signedInUser };
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => {
          calls.push(['getSession']);
          return { data: { session: null }, error: null };
        },
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        exchangeCodeForSession: async (code) => {
          calls.push(['exchangeCodeForSession', code]);
          return { data: { session: recoverySession, user: signedInUser }, error: null };
        },
      },
    }),
  });

  const result = await authClient.preparePasswordRecovery(
    'https://app.example.com/reset-password?code=recovery-code',
  );

  assert.equal(result.success, true);
  assert.equal(result.data.session, recoverySession);
  assert.equal(authClient.isValid, true);
  assert.equal(authClient.model.email, 'mae@example.com');
  assert.deepEqual(calls, [['exchangeCodeForSession', 'recovery-code']]);
});

test('Supabase auth prepares password recovery from an existing recovery session', async () => {
  const signedInUser = {
    id: 'user-123',
    email: 'mae@example.com',
    user_metadata: { name: 'Mae' },
  };
  const recoverySession = { user: signedInUser };
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => ({ data: { session: recoverySession }, error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
      },
    }),
  });

  const result = await authClient.preparePasswordRecovery('https://app.example.com/reset-password');

  assert.equal(result.success, true);
  assert.equal(result.data.session, recoverySession);
  assert.equal(authClient.isValid, true);
});

test('Supabase auth rejects password recovery when the redirect has an error', async () => {
  let getSessionCalled = false;
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => {
          getSessionCalled = true;
          return { data: { session: null }, error: null };
        },
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
      },
    }),
  });

  const result = await authClient.preparePasswordRecovery(
    'https://app.example.com/reset-password#error=access_denied&error_description=Link%20expired',
  );

  assert.equal(result.success, false);
  assert.match(result.error, /Link expired/);
  assert.equal(getSessionCalled, false);
});

test('Supabase auth rejects password update without an active recovery session', async () => {
  let updateUserCalled = false;
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        updateUser: async () => {
          updateUserCalled = true;
          return { data: {}, error: null };
        },
      },
    }),
  });

  const result = await authClient.updatePassword('NovaSenha123');

  assert.equal(result.success, false);
  assert.match(result.error, /link de recuperacao/i);
  assert.equal(updateUserCalled, false);
});

test('Supabase auth returns a clear message when email is not confirmed', async () => {
  const authClient = createAuthClient({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => ({
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        signInWithPassword: async () => ({
          data: { session: null },
          error: { message: 'Email not confirmed' },
        }),
      },
    }),
  });

  const result = await authClient.login('mae@example.com', 'Senha123');

  assert.equal(result.success, false);
  assert.match(result.error, /e-mail ainda não foi confirmado/i);
});

test('createAuthClient can read Supabase config from runtime config file', () => {
  const originalConfig = globalThis.__MINERVA_CONFIG__;
  const calls = [];

  globalThis.__MINERVA_CONFIG__ = {
    VITE_SUPABASE_URL: 'https://runtime.supabase.co',
    VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_runtime',
  };

  createAuthClient({
    createSupabaseClient: (url, key) => {
      calls.push([url, key]);

      return {
        auth: {
          getSession: async () => ({ data: { session: null }, error: null }),
          onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        },
      };
    },
  });

  assert.deepEqual(calls, [['https://runtime.supabase.co', 'sb_publishable_runtime']]);

  if (originalConfig === undefined) {
    delete globalThis.__MINERVA_CONFIG__;
  } else {
    globalThis.__MINERVA_CONFIG__ = originalConfig;
  }
});

test('explicit local mode isolates development from a configured Supabase project', async () => {
  let supabaseCreated = false;
  const storage = createMemoryStorage();
  const authClient = createAuthClient({
    authMode: 'local',
    appEnvironment: 'development',
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'sb_publishable_test',
    createSupabaseClient: () => {
      supabaseCreated = true;
      throw new Error('Supabase must not be initialized in local mode.');
    },
    storage,
  });

  assert.deepEqual(
    await authClient.signup('e2e@example.com', 'Senha123', 'Familia E2E'),
    { success: true },
  );
  assert.equal(supabaseCreated, false);
});

test('production refuses local identity mode', () => {
  assert.throws(
    () => createAuthClient({ authMode: 'local', appEnvironment: 'production' }),
    /local não pode ser habilitada/i,
  );
});

test('unsupported identity modes fail closed in development', () => {
  assert.throws(
    () => createAuthClient({
      authMode: 'legacy-provider',
      appEnvironment: 'development',
    }),
    /Modo de autenticação não suportado/i,
  );
});

test('production requires a complete Supabase configuration', () => {
  assert.throws(
    () => createAuthClient({
      authMode: 'supabase',
      appEnvironment: 'production',
      supabaseUrl: '',
      supabasePublishableKey: '',
    }),
    /Supabase Auth exige URL e chave pública/i,
  );
  assert.throws(
    () => createAuthClient({
      authMode: '',
      appEnvironment: 'production',
      supabaseUrl: '',
      supabasePublishableKey: '',
      pocketBaseUrl: '',
    }),
    /Supabase Auth e obrigatorio/i,
  );
});
