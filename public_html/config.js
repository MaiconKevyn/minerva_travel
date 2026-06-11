window.__MINERVA_CONFIG__ = {
  MINERVA_APP_VERSION: '20260611-chrome-cache-guard',
  VITE_SUPABASE_URL: 'https://khxltgyqmaypdnfjjtak.supabase.co',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_knCWQ4yFRkz2tlRwjNT-Mw_E_syLVVZ',
  VITE_GOOGLE_MAPS_BROWSER_KEY: 'AIzaSyA4SCkhVq_NZ_6juuFtk3TW2isVws_thzM',
  VITE_GOOGLE_MAPS_MAP_ID: '7c07de202bcca1de5c3b170c',
};

(() => {
  const currentModuleEntry = () => {
    const script = document.querySelector('script[type="module"][src*="/assets/"]');
    return script?.src || '';
  };

  const latestModuleEntry = async () => {
    const response = await fetch(`/index.html?minerva_cache_check=${Date.now()}`, {
      cache: 'no-store',
    });
    if (!response.ok) {
      return '';
    }
    const html = await response.text();
    const match = html.match(/<script\s+type="module"[^>]*\ssrc="([^"]+)"/);
    return match?.[1] ? new URL(match[1], window.location.origin).href : '';
  };

  window.addEventListener('DOMContentLoaded', async () => {
    try {
      const current = currentModuleEntry();
      const latest = await latestModuleEntry();
      if (!latest || current === latest) {
        return;
      }

      const reloadKey = 'minerva_cache_guard_reloaded_for';
      const runtimeVersion = window.__MINERVA_CONFIG__?.MINERVA_APP_VERSION || 'unknown';
      const reloadToken = `${runtimeVersion}:${latest}`;
      if (sessionStorage.getItem(reloadKey) === reloadToken) {
        return;
      }

      sessionStorage.setItem(reloadKey, reloadToken);
      window.location.reload();
    } catch (error) {
      console.warn('Minerva cache check skipped:', error);
    }
  });
})();
