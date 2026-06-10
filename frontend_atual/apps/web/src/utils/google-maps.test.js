import assert from 'node:assert/strict';
import test from 'node:test';
import { googleMapsLibraries } from './google-maps.js';

test('googleMapsLibraries falls back to classic Google Maps globals', async () => {
  const Map = function ClassicMap() {};
  const AdvancedMarkerElement = function AdvancedMarkerElement() {};
  const google = {
    maps: {
      Map,
      marker: { AdvancedMarkerElement },
    },
  };

  const libraries = await googleMapsLibraries(google, { includeMarker: true });

  assert.equal(libraries.Map, Map);
  assert.equal(libraries.markerLibrary.AdvancedMarkerElement, AdvancedMarkerElement);
});

test('googleMapsLibraries uses importLibrary when available', async () => {
  const Map = function ImportedMap() {};
  const AdvancedMarkerElement = function ImportedAdvancedMarkerElement() {};
  const calls = [];
  const google = {
    maps: {
      async importLibrary(library) {
        calls.push(library);
        if (library === 'maps') return { Map };
        if (library === 'marker') return { AdvancedMarkerElement };
        return {};
      },
    },
  };

  const libraries = await googleMapsLibraries(google, { includeMarker: true });

  assert.deepEqual(calls, ['maps', 'marker']);
  assert.equal(libraries.Map, Map);
  assert.equal(libraries.markerLibrary.AdvancedMarkerElement, AdvancedMarkerElement);
});
