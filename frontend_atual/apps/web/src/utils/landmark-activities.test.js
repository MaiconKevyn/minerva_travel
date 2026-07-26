import assert from 'node:assert/strict';
import test from 'node:test';

import {
  LANDMARK_ACTIVITY_OPTIONS,
  MAX_OPTIONAL_ACTIVITIES_PER_GUIDE,
  MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK,
  OPTIONAL_LANDMARK_ACTIVITY_TYPES,
  activityGallery,
  normalizeLandmarkActivitySelections,
  pruneLandmarkActivitySelections,
  toggleLandmarkActivitySelection,
} from './landmark-activities.js';

test('coloring preview promises child-friendly point-specific artwork', () => {
  const coloring = LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === 'coloring');

  assert.equal(coloring.preview, '/activity-examples/coloring-real.webp');
  assert.match(coloring.description, /traços limpos, formas grandes/);
  assert.match(coloring.description, /frase personalizada/);
});

test('painting replaces the free drawing activity without changing persisted type', () => {
  const painting = LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === 'drawing');

  assert.equal(painting.label, 'Minha pintura');
  assert.equal(painting.preview, '/activity-examples/painting-real.webp');
  assert.match(painting.description, /criar uma pintura/);
  // O rótulo encurtou para caber no card compacto, mas segue anunciando tinta.
  assert.match(painting.materialLabel, /Tinta/);
});

test('family vacation coloring uses the private family photo and an original visual description', () => {
  const familyColoring = LANDMARK_ACTIVITY_OPTIONS.find(
    (option) => option.type === 'family_coloring',
  );

  assert.equal(familyColoring.label, 'Família de férias para colorir');
  assert.equal(
    familyColoring.preview,
    '/activity-examples/family-coloring-real.webp',
  );
  assert.match(familyColoring.description, /foto enviada como referência/);
});

test('investigator assigns an age-aware contextual mission to every child', () => {
  const investigator = LANDMARK_ACTIVITY_OPTIONS.find(
    (option) => option.type === 'investigator',
  );

  assert.equal(investigator.label, 'Investigador');
  assert.equal(investigator.preview, '/activity-examples/investigator-real.webp');
  assert.match(investigator.description, /Cada criança recebe uma pista/);
  assert.match(investigator.description, /adaptada à idade e ao ponto turístico/);
});

test('activity selections are normalized to canonical point ids and supported types', () => {
  assert.deepEqual(
    normalizeLandmarkActivitySelections([
      { landmark_selection_id: ' paris:eiffel ', activity_type: 'coloring' },
      { landmark_selection_id: 'paris:eiffel', activity_type: 'coloring' },
      { landmark_selection_id: 'paris:eiffel', activity_type: 'unsupported' },
      { landmark_selection_id: '', activity_type: 'drawing' },
      { landmark_selection_id: 'paris:louvre', activity_type: 'family_coloring' },
      { landmark_selection_id: 'roma:pantheon', activity_type: 'investigator' },
    ]),
    [
      { landmark_selection_id: 'paris:eiffel', activity_type: 'coloring', order: 1 },
      { landmark_selection_id: 'paris:louvre', activity_type: 'family_coloring', order: 1 },
      { landmark_selection_id: 'roma:pantheon', activity_type: 'investigator', order: 1 },
    ],
  );
});

test('activity selection enforces the per-landmark limit', () => {
  // Derivado do limite: com um número fixo, afrouxá-lo faria o teste passar
  // sem exercitar a regra.
  let selections = [];
  OPTIONAL_LANDMARK_ACTIVITY_TYPES.slice(0, MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK).forEach(
    (type) => {
      selections = toggleLandmarkActivitySelection(selections, 'paris:eiffel', type).selections;
    },
  );
  const oneTooMany = OPTIONAL_LANDMARK_ACTIVITY_TYPES[MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK];
  const rejected = toggleLandmarkActivitySelection(selections, 'paris:eiffel', oneTooMany);

  assert.equal(selections.length, MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK);
  assert.equal(rejected.selections.length, MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK);
  assert.match(
    rejected.error,
    new RegExp(`no máximo ${MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK} atividades por ponto`),
  );
});

test('activity selection enforces the guide quota and permits deselection', () => {
  let selections = [];
  for (let index = 0; selections.length < MAX_OPTIONAL_ACTIVITIES_PER_GUIDE; index += 1) {
    selections = toggleLandmarkActivitySelection(selections, `point-${index}`, 'drawing').selections;
    selections = toggleLandmarkActivitySelection(selections, `point-${index}`, 'coloring').selections;
  }

  const rejected = toggleLandmarkActivitySelection(selections, 'point-999', 'word_search');
  assert.equal(selections.length, MAX_OPTIONAL_ACTIVITIES_PER_GUIDE);
  assert.match(
    rejected.error,
    new RegExp(`no máximo ${MAX_OPTIONAL_ACTIVITIES_PER_GUIDE} atividades opcionais por guia`),
  );

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

test('activity gallery falls back to the single printed page', () => {
  const detailHunt = LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === 'detail_hunt');
  const gallery = activityGallery(detailHunt);

  assert.equal(gallery.length, 1);
  assert.equal(gallery[0].src, detailHunt.preview);
  assert.ok(gallery[0].caption);
});

test('puzzles show the solved page next to the blank one', () => {
  // Ver a atividade pronta é o que responde "o que isso é" para um pai que
  // nunca viu a página.
  for (const type of ['word_search', 'maze', 'crossword', 'dot_to_dot']) {
    const activity = LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === type);
    const gallery = activityGallery(activity);

    assert.equal(gallery.length, 2, type);
    assert.notEqual(gallery[0].src, gallery[1].src, type);
    assert.match(gallery[1].src, /-solved\.webp$/, type);
    assert.ok(gallery.every((item) => item.label && item.caption), type);
  }
});

test('every activity offers a longer description for the expanded view', () => {
  for (const activity of LANDMARK_ACTIVITY_OPTIONS) {
    assert.ok(activity.about, activity.type);
    // O modal existe para dizer mais que o card; repetir não serviria.
    assert.notEqual(activity.about, activity.description, activity.type);
    assert.ok(activity.about.length > activity.description.length, activity.type);
  }
});

test('the catalogue shows many landmarks, not the same one eighteen times', () => {
  // Abrir dezoito cards e ver a mesma Torre Eiffel não mostra que a página se
  // adapta a cada parada — mostra o contrário.
  const sources = LANDMARK_ACTIVITY_OPTIONS.flatMap((activity) =>
    activityGallery(activity).map((item) => item.src),
  );

  assert.equal(new Set(sources).size, sources.length);
  assert.ok(sources.every((src) => src.startsWith('/activity-examples/')));
  assert.ok(sources.every((src) => src.endsWith('.webp')));
});

test('spot the difference shows both scenes whole, not only the composed page', () => {
  const activity = LANDMARK_ACTIVITY_OPTIONS.find(
    (option) => option.type === 'spot_the_difference',
  );
  const gallery = activityGallery(activity);

  // Comparar dois desenhos exige ver os dois; a página montada os reduz.
  assert.equal(gallery.length, 3);
  assert.match(gallery[1].src, /scene-1/);
  assert.match(gallery[2].src, /scene-2/);
});
