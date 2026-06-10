let googleMapsLoaderPromise = null;
const GOOGLE_MAPS_SCRIPT_ID = 'minerva-google-maps-js';
const GOOGLE_MAPS_CALLBACK = '__minervaGoogleMapsLoaded';

const runtimeConfig = () => globalThis.__MINERVA_CONFIG__ || {};

export const googleMapsBrowserKey = () => (
  import.meta.env?.VITE_GOOGLE_MAPS_BROWSER_KEY ||
  runtimeConfig().VITE_GOOGLE_MAPS_BROWSER_KEY ||
  ''
);

export const googleMapsMapId = () => (
  import.meta.env?.VITE_GOOGLE_MAPS_MAP_ID ||
  runtimeConfig().VITE_GOOGLE_MAPS_MAP_ID ||
  ''
);

export const loadGoogleMaps = (apiKey) => {
  if (globalThis.google?.maps?.importLibrary) {
    return Promise.resolve(globalThis.google);
  }

  if (globalThis.google?.maps?.Map) {
    return Promise.resolve(globalThis.google);
  }

  if (!googleMapsLoaderPromise) {
    googleMapsLoaderPromise = new Promise((resolve, reject) => {
      const existing = document.getElementById(GOOGLE_MAPS_SCRIPT_ID);
      globalThis[GOOGLE_MAPS_CALLBACK] = () => resolve(globalThis.google);

      if (existing) {
        existing.addEventListener('load', () => {
          if (globalThis.google?.maps?.Map || globalThis.google?.maps?.importLibrary) {
            resolve(globalThis.google);
          }
        }, { once: true });
        existing.addEventListener('error', reject, { once: true });
        return;
      }

      const script = document.createElement('script');
      const params = new URLSearchParams({
        key: apiKey,
        v: 'weekly',
        libraries: 'marker',
        loading: 'async',
        callback: GOOGLE_MAPS_CALLBACK,
      });
      const mapId = googleMapsMapId();

      if (mapId) {
        params.set('map_ids', mapId);
      }

      script.id = GOOGLE_MAPS_SCRIPT_ID;
      script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
      script.async = true;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  return googleMapsLoaderPromise;
};

export const googleMapsLibraries = async (google, { includeMarker = false } = {}) => {
  if (typeof google?.maps?.importLibrary === 'function') {
    const mapsLibrary = await google.maps.importLibrary('maps');
    const markerLibrary = includeMarker
      ? await google.maps.importLibrary('marker').catch(() => ({}))
      : {};

    return {
      Map: mapsLibrary.Map || google.maps.Map,
      markerLibrary,
    };
  }

  return {
    Map: google?.maps?.Map,
    markerLibrary: google?.maps?.marker || {},
  };
};

export const clearGoogleMarkers = (markers = []) => {
  markers.filter(Boolean).forEach((marker) => {
    if ('map' in marker) {
      marker.map = null;
    } else if (typeof marker.setMap === 'function') {
      marker.setMap(null);
    }
  });
};
