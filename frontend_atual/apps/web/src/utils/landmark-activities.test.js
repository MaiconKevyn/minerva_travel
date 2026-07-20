import assert from 'node:assert/strict';
import test from 'node:test';

import {
  LANDMARK_ACTIVITY_OPTIONS,
  MAX_OPTIONAL_ACTIVITIES_PER_GUIDE,
  MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK,
  normalizeLandmarkActivitySelections,
  pruneLandmarkActivitySelections,
  toggleLandmarkActivitySelection,
} from './landmark-activities.js';

test('coloring preview promises child-friendly point-specific artwork', () => {
  const coloring = LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === 'coloring');

  assert.equal(coloring.preview, '/activity-examples/coloring.svg');
  assert.match(coloring.description, /traços limpos, formas grandes/);
  assert.match(coloring.description, /frase personalizada/);
});

test('painting replaces the free drawing activity without changing persisted type', () => {
  const painting = LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === 'drawing');

  assert.equal(painting.label, 'Minha pintura');
  assert.equal(painting.preview, '/activity-examples/painting.svg');
  assert.match(painting.description, /criar uma pintura/);
  assert.match(painting.materialLabel, /Tinta, pincel/);
});

test('activity selections are normalized to canonical point ids and supported types', () => {
  assert.deepEqual(
    normalizeLandmarkActivitySelections([
      { landmark_selection_id: ' paris:eiffel ', activity_type: 'coloring' },
      { landmark_selection_id: 'paris:eiffel', activity_type: 'coloring' },
      { landmark_selection_id: 'paris:eiffel', activity_type: 'unsupported' },
      { landmark_selection_id: '', activity_type: 'drawing' },
    ]),
    [{ landmark_selection_id: 'paris:eiffel', activity_type: 'coloring', order: 1 }],
  );
});

test('activity selection enforces two pages per landmark', () => {
  let selections = [];
  selections = toggleLandmarkActivitySelection(selections, 'paris:eiffel', 'detail_hunt').selections;
  selections = toggleLandmarkActivitySelection(selections, 'paris:eiffel', 'word_search').selections;
  const rejected = toggleLandmarkActivitySelection(selections, 'paris:eiffel', 'coloring');

  assert.equal(selections.length, MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK);
  assert.equal(rejected.selections.length, MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK);
  assert.match(rejected.error, /no máximo 2 atividades por ponto turístico/);
});

test('activity selection enforces the guide quota and permits deselection', () => {
  let selections = [];
  for (let index = 0; index < 4; index += 1) {
    selections = toggleLandmarkActivitySelection(selections, `point-${index}`, 'drawing').selections;
    selections = toggleLandmarkActivitySelection(selections, `point-${index}`, 'coloring').selections;
  }

  const rejected = toggleLandmarkActivitySelection(selections, 'point-5', 'word_search');
  assert.equal(selections.length, MAX_OPTIONAL_ACTIVITIES_PER_GUIDE);
  assert.match(rejected.error, /no máximo 8 atividades opcionais por guia/);

  const removed = toggleLandmarkActivitySelection(selections, 'point-0', 'drawing');
  assert.equal(removed.error, '');
  assert.equal(removed.selections.length, MAX_OPTIONAL_ACTIVITIES_PER_GUIDE - 1);
});

test('activity selections are pruned when a landmark is removed', () => {
  const selections = [
    { landmark_selection_id: 'paris:eiffel', activity_type: 'coloring' },
    { landmark_selection_id: 'paris:louvre', activity_type: 'drawing' },
  ];

  assert.deepEqual(pruneLandmarkActivitySelections(selections, ['paris:louvre']), [
    { landmark_selection_id: 'paris:louvre', activity_type: 'drawing', order: 1 },
  ]);
});
