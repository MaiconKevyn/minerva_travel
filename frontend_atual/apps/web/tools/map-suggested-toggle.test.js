import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('trip map starts with confirmed points and exposes suggested toggle', () => {
  const modal = readProjectFile('src/components/MapOverviewModal.jsx');

  assert.match(modal, /showSuggestedOnMap/);
  assert.match(modal, /Mostrar sugeridos/);
  assert.match(modal, /tripMapVisibleItems/);
});

test('trip map falls back when advanced markers or bounds fail', () => {
  const modal = readProjectFile('src/components/MapOverviewModal.jsx');

  assert.match(modal, /createTripMapMarker/);
  assert.match(modal, /fitTripMapView/);
  assert.match(modal, /Advanced marker unavailable/);
  assert.match(modal, /landmarks\.length === 1/);
});
