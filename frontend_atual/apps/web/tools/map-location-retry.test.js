import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('confirmed attraction step validates and retries map locations', () => {
  const step = readProjectFile('src/components/Step4Attractions.jsx');

  assert.match(step, /missingSelectedMapLandmarks/);
  assert.match(step, /mergeResolvedLandmarkLocations/);
  assert.match(step, /retryResolveMapLocations/);
  assert.match(step, /hasMissingMapLocations/);
  assert.match(step, /Tentar localizar no mapa/);
});
