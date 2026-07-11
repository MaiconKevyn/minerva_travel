import { createClient as createSupabaseClient } from '@supabase/supabase-js';

const LOCAL_USERS_KEY = 'minerva_local_users';
const LOCAL_SESSION_KEY = 'minerva_local_session';
const PASSWORD_RECOVERY_REQUIRED_MESSAGE = (
  'Link de recuperacao invalido ou expirado. Solicite um novo email de recuperacao de senha.'
);

const runtimeConfig = () => globalThis.__MINERVA_CONFIG__ || {};

const parseJson = (value, fallback) => {
  if (!value) {
    return fallback;
  }

  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
};

export const createMemoryStorage = () => {
  const store = new Map();

  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => {
      store.set(key, String(value));
    },
    removeItem: (key) => {
      store.delete(key);
    },
  };
};

const normalizeEmail = (email) => email.trim().toLowerCase();

const authParamsFromUrl = (currentUrl) => {
  if (!currentUrl) {
    return new URLSearchParams();
  }

  try {
    const url = new URL(currentUrl, globalThis.location?.origin || 'https://minerva.local');
    const params = new URLSearchParams(url.search);
    const hash = url.hash.startsWith('#') ? url.hash.slice(1) : url.hash;
    const hashParams = new URLSearchParams(hash);

    hashParams.forEach((value, key) => {
      if (!params.has(key)) {
        params.set(key, value);
      }
    });

    return params;
  } catch {
    return new URLSearchParams();
  }
};

const createUserModel = ({ email, name }) => ({
  id: `local:${email}`,
  email,
  name,
  collectionName: 'users',
});

const formatAuthError = (error, fallback) => {
  const message = error?.message || '';
  const normalized = message.toLowerCase();

  if (normalized.includes('email not confirmed')) {
    return 'Este e-mail ainda não foi confirmado. Verifique sua caixa de entrada ou desative a confirmação de e-mail no Supabase para o MVP.';
  }

  if (normalized.includes('invalid login credentials')) {
    return 'Email ou senha incorretos. Se sua conta foi criada antes do Supabase, crie uma nova conta.';
  }

  return message || fallback;
};

const createSupabaseUserModel = (user) => {
  if (!user) {
    return null;
  }

  const email = user.email || '';
  const name = user.user_metadata?.name || user.user_metadata?.full_name || email;

  return {
    id: user.id,
    email,
    name,
    collectionName: 'users',
  };
};

const toHex = (bytes) => Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');

const createPasswordDigest = async (email, password) => {
  const input = new TextEncoder().encode(`${email}:${password}`);

  if (globalThis.crypto?.subtle) {
    const digest = await globalThis.crypto.subtle.digest('SHA-256', input);
    return `sha256:${toHex(new Uint8Array(digest))}`;
  }

  return `hex:${toHex(input)}`;
};

export const createLocalAuthClient = (storage = globalThis.localStorage || createMemoryStorage()) => {
  const listeners = new Set();

  const readUsers = () => parseJson(storage.getItem(LOCAL_USERS_KEY), {});
  const writeUsers = (users) => storage.setItem(LOCAL_USERS_KEY, JSON.stringify(users));
  const readSession = () => parseJson(storage.getItem(LOCAL_SESSION_KEY), null);

  const notify = () => {
    const session = readSession();
    listeners.forEach((listener) => listener(session));
  };

  return {
    get model() {
      return readSession();
    },

    get isValid() {
      return Boolean(readSession());
    },

    subscribe(listener) {
      listeners.add(listener);

      return () => {
        listeners.delete(listener);
      };
    },

    async initialize() {
      notify();
      return readSession();
    },

    async getAccessToken() {
      return readSession() ? 'local-development-token' : null;
    },

    async login(email, password) {
      const users = readUsers();
      const normalizedEmail = normalizeEmail(email);
      const user = users[normalizedEmail];
      const passwordDigest = user ? await createPasswordDigest(normalizedEmail, password) : null;

      if (!user || user.passwordDigest !== passwordDigest) {
        return { success: false, error: 'Login falhou. Verifique suas credenciais.' };
      }

      const model = createUserModel(user);
      storage.setItem(LOCAL_SESSION_KEY, JSON.stringify(model));
      notify();

      return { success: true, data: { record: model, token: `local:${normalizedEmail}` } };
    },

    async signup(email, password, name) {
      const users = readUsers();
      const normalizedEmail = normalizeEmail(email);

      if (users[normalizedEmail]) {
        return { success: false, error: 'Este e-mail já está cadastrado.' };
      }

      const passwordDigest = await createPasswordDigest(normalizedEmail, password);

      users[normalizedEmail] = {
        email: normalizedEmail,
        passwordDigest,
        name: String(name || '').trim() || normalizedEmail,
      };
      writeUsers(users);

      return { success: true };
    },

    async requestPasswordReset() {
      return {
        success: false,
        error: 'Recuperação de senha exige Supabase configurado.',
      };
    },

    async preparePasswordRecovery() {
      return {
        success: false,
        error: 'Recuperação de senha exige Supabase configurado.',
      };
    },

    async updatePassword() {
      return {
        success: false,
        error: 'Recuperação de senha exige Supabase configurado.',
      };
    },

    logout() {
      storage.removeItem(LOCAL_SESSION_KEY);
      notify();
    },
  };
};

export const createSupabaseAuthClient = ({
  supabaseUrl,
  supabasePublishableKey,
  createClient = createSupabaseClient,
}) => {
  const supabase = createClient(supabaseUrl, supabasePublishableKey);
  const listeners = new Set();
  let currentUser = null;

  const setSession = (session) => {
    currentUser = createSupabaseUserModel(session?.user);
    listeners.forEach((listener) => listener(currentUser));
  };

  return {
    get model() {
      return currentUser;
    },

    get isValid() {
      return Boolean(currentUser);
    },

    subscribe(listener) {
      listeners.add(listener);

      const { data } = supabase.auth.onAuthStateChange((event, session) => {
        setSession(session);
      });

      return () => {
        listeners.delete(listener);
        data?.subscription?.unsubscribe();
      };
    },

    async initialize() {
      const { data, error } = await supabase.auth.getSession();

      if (error) {
        console.error('Supabase session error:', error);
        setSession(null);
        return null;
      }

      setSession(data?.session || null);
      return currentUser;
    },

    async getAccessToken() {
      const { data, error } = await supabase.auth.getSession();
      if (error) {
        console.error('Supabase session error:', error);
        return null;
      }
      return data?.session?.access_token || null;
    },

    async login(email, password) {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });

      if (error) {
        console.error('Login error:', error);
        return { success: false, error: formatAuthError(error, 'Login falhou. Verifique suas credenciais.') };
      }

      setSession(data?.session || (data?.user ? { user: data.user } : null));

      return { success: true, data };
    },

    async signup(email, password, name) {
      const cleanName = String(name || '').trim();
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { name: cleanName } },
      });

      if (error) {
        console.error('Signup error:', error);
        return { success: false, error: formatAuthError(error, 'Falha ao criar conta.') };
      }

      if (data?.session) {
        setSession(data.session);
      }

      return { success: true, data };
    },

    async requestPasswordReset(email, redirectTo) {
      const options = redirectTo ? { redirectTo } : undefined;
      const { data, error } = await supabase.auth.resetPasswordForEmail(email, options);

      if (error) {
        console.error('Password reset error:', error);
        return { success: false, error: formatAuthError(error, 'Falha ao enviar email de recuperacao.') };
      }

      return { success: true, data };
    },

    async preparePasswordRecovery(currentUrl = globalThis.location?.href || '') {
      const params = authParamsFromUrl(currentUrl);
      const redirectError = params.get('error_description') || params.get('error');

      if (redirectError) {
        return { success: false, error: redirectError };
      }

      const code = params.get('code');

      if (code && typeof supabase.auth.exchangeCodeForSession === 'function') {
        const { data, error } = await supabase.auth.exchangeCodeForSession(code);

        if (error) {
          console.error('Password recovery code exchange error:', error);
          return { success: false, error: formatAuthError(error, PASSWORD_RECOVERY_REQUIRED_MESSAGE) };
        }

        if (data?.session) {
          setSession(data.session);
          return { success: true, data };
        }
      }

      const { data, error } = await supabase.auth.getSession();

      if (error) {
        console.error('Password recovery session error:', error);
        setSession(null);
        return { success: false, error: formatAuthError(error, PASSWORD_RECOVERY_REQUIRED_MESSAGE) };
      }

      if (!data?.session) {
        setSession(null);
        return { success: false, error: PASSWORD_RECOVERY_REQUIRED_MESSAGE };
      }

      setSession(data.session);
      return { success: true, data };
    },

    async updatePassword(password) {
      const sessionResult = await supabase.auth.getSession();

      if (sessionResult.error) {
        console.error('Password recovery session error:', sessionResult.error);
        return {
          success: false,
          error: formatAuthError(sessionResult.error, PASSWORD_RECOVERY_REQUIRED_MESSAGE),
        };
      }

      if (!sessionResult.data?.session) {
        return {
          success: false,
          error: PASSWORD_RECOVERY_REQUIRED_MESSAGE,
        };
      }

      const { data, error } = await supabase.auth.updateUser({ password });

      if (error) {
        console.error('Password update error:', error);
        return { success: false, error: formatAuthError(error, 'Falha ao atualizar senha.') };
      }

      setSession(data?.user ? { user: data.user } : null);

      return { success: true, data };
    },

    async logout() {
      const { error } = await supabase.auth.signOut();

      if (error) {
        console.error('Logout error:', error);
      }

      setSession(null);
    },
  };
};

export const createAuthClient = ({
  authMode = import.meta.env?.VITE_AUTH_MODE || runtimeConfig().VITE_AUTH_MODE,
  appEnvironment = (
    import.meta.env?.VITE_APP_ENV ||
    runtimeConfig().VITE_APP_ENV ||
    (import.meta.env?.PROD ? 'production' : 'development')
  ),
  supabaseUrl = import.meta.env?.VITE_SUPABASE_URL || runtimeConfig().VITE_SUPABASE_URL,
  supabasePublishableKey = (
    import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY || runtimeConfig().VITE_SUPABASE_PUBLISHABLE_KEY
  ),
  createSupabaseClient: createSupabaseClientOverride = createSupabaseClient,
  storage = globalThis.localStorage,
} = {}) => {
  const environment = String(appEnvironment || 'development').trim().toLowerCase();
  const selectedMode = String(authMode || '').trim().toLowerCase();
  const production = environment === 'production';

  if (selectedMode === 'local') {
    if (production) {
      throw new Error('Autenticação local não pode ser habilitada em produção.');
    }
    return createLocalAuthClient(storage || createMemoryStorage());
  }

  if (selectedMode === 'supabase' || (!selectedMode && supabaseUrl && supabasePublishableKey)) {
    if (!supabaseUrl || !supabasePublishableKey) {
      throw new Error('Supabase Auth exige URL e chave pública configuradas.');
    }
    return createSupabaseAuthClient({
      supabaseUrl,
      supabasePublishableKey,
      createClient: createSupabaseClientOverride,
    });
  }

  if (production) {
    throw new Error('Supabase Auth e obrigatorio em producao.');
  }

  if (selectedMode) {
    throw new Error(`Modo de autenticação não suportado: ${selectedMode}.`);
  }

  return createLocalAuthClient(storage || createMemoryStorage());
};

const authClient = createAuthClient();

export default authClient;
