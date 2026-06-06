import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('selection landmark cards stay focused on essential information', () => {
  const card = readProjectFile('src/components/LandmarkCard.jsx');

  assert.doesNotMatch(card, /match_reasons/);
  assert.doesNotMatch(card, /family_tip/);
  assert.doesNotMatch(card, /confidence/);
  assert.doesNotMatch(card, /Alta Compatibilidade|Boa Op..o/);
  assert.doesNotMatch(card, /Marque no livrinho/);
  assert.doesNotMatch(card, /Ponto obrigatorio informado pela familia/);
  assert.doesNotMatch(card, /Bem avaliado por viajantes/);
});
