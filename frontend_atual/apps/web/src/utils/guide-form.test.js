import assert from 'node:assert/strict';
import test from 'node:test';

import * as guideForm from './guide-form.js';
import {
  deriveChildAges,
  deriveChildNames,
  guideChildRecordsForSubmit,
  normalizeGuideDestinations,
  serializeGuideDestinations,
  totalTripDays,
  validGuideChildren,
  validGuideDestinations,
} from './guide-form.js';

test('serializeGuideDestinations preserves place timing duration and order', () => {
  const destinations = normalizeGuideDestinations([
    { id: 'first', place: 'Paris, França', timing: 'Julho de 2026', days: '3' },
    { id: 'second', place: 'Londres', timing: 'depois de Paris', days: 2 },
  ]);

  assert.deepEqual(destinations, [
    { id: 'first', place: 'Paris, França', timing: 'Julho de 2026', days: 3, landmarks: [] },
    { id: 'second', place: 'Londres', timing: 'depois de Paris', days: 2, landmarks: [] },
  ]);
  assert.equal(
    serializeGuideDestinations(destinations),
    'Destino 1: Paris, França; quando: Julho de 2026; duração: 3 dias.\nDestino 2: Londres; quando: depois de Paris; duração: 2 dias.',
  );
  assert.equal(totalTripDays(destinations), 5);
});

test('createGuideDestination keeps IDs unique when a destination is removed and another is added', () => {
  const destinations = [
    guideForm.createGuideDestination(),
    guideForm.createGuideDestination(),
    guideForm.createGuideDestination(),
  ];
  const removedId = destinations[1].id;
  const afterRemoval = destinations.filter((destination) => destination.id !== removedId);
  const afterAddition = [...afterRemoval, guideForm.createGuideDestination()];

  assert.equal(new Set(afterAddition.map((destination) => destination.id)).size, 3);
  assert.notEqual(afterAddition.at(-1).id, removedId);
  assert.match(afterAddition.at(-1).id, /^destination-/);
});

test('family member limits match the current guide contract', () => {
  assert.equal(guideForm.MAX_GUIDE_CHILDREN, 10);
  assert.equal(guideForm.MAX_GUIDE_PARENTS, 10);
});

test('validateFamilyPhoto accepts a matching PNG within byte and dimension limits', async () => {
  const pngHeader = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const file = new File([pngHeader], 'familia.png', { type: 'image/png' });

  const result = await guideForm.validateFamilyPhoto(file, {
    decodeDimensions: async () => ({ width: 1200, height: 800 }),
  });

  assert.deepEqual(result, { valid: true, code: 'valid_image', message: '' });
});

test('validateFamilyPhoto rejects fake image content and unsupported declarations', async () => {
  const fakePng = new File([Uint8Array.from([1, 2, 3, 4])], 'familia.png', {
    type: 'image/png',
  });
  const svg = new File(['<svg></svg>'], 'familia.svg', { type: 'image/svg+xml' });

  assert.equal((await guideForm.validateFamilyPhoto(fakePng)).code, 'content_mismatch');
  assert.equal((await guideForm.validateFamilyPhoto(svg)).code, 'unsupported_type');
});

test('validateFamilyPhoto rejects excessive file and pixel dimensions before upload', async () => {
  const oversized = {
    name: 'familia.jpg',
    type: 'image/jpeg',
    size: guideForm.FAMILY_PHOTO_MAX_BYTES + 1,
    slice: () => {
      throw new Error('Large file should be rejected before reading.');
    },
  };
  const jpeg = new File([Uint8Array.from([0xff, 0xd8, 0xff, 0x00])], 'familia.jpg', {
    type: 'image/jpeg',
  });

  assert.equal((await guideForm.validateFamilyPhoto(oversized)).code, 'file_too_large');
  assert.equal(
    (await guideForm.validateFamilyPhoto(jpeg, {
      decodeDimensions: async () => ({ width: 12_001, height: 100 }),
    })).code,
    'dimensions_exceeded',
  );
});

test('normalizeGuideDestinations trims landmark names and drops empty boxes', () => {
  const destinations = normalizeGuideDestinations([
    {
      id: 'first',
      place: 'Paris, França',
      timing: 'Julho de 2026',
      days: 3,
      landmarks: [' Torre Eiffel ', '', 'Museu do Louvre', '   '],
    },
  ]);

  assert.deepEqual(destinations[0].landmarks, ['Torre Eiffel', 'Museu do Louvre']);
  assert.equal(
    serializeGuideDestinations(destinations),
    'Destino 1: Paris, França; quando: Julho de 2026; duração: 3 dias. pontos turísticos: Torre Eiffel, Museu do Louvre.',
  );
});

test('validKnownGuideDestinations requires at least one landmark per destination', () => {
  const base = { place: 'Paris', timing: 'Julho', days: 3 };

  assert.equal(
    guideForm.validKnownGuideDestinations([{ ...base, landmarks: ['Torre Eiffel'] }]),
    true,
  );
  assert.equal(guideForm.validKnownGuideDestinations([{ ...base, landmarks: ['  '] }]), false);
  assert.equal(guideForm.validKnownGuideDestinations([{ ...base }]), false);
  assert.equal(
    guideForm.validKnownGuideDestinations([
      { ...base, landmarks: ['Torre Eiffel'] },
      { place: 'Roma', timing: 'Agosto', days: 2, landmarks: [] },
    ]),
    false,
  );
});

test('validGuideDestinations requires place timing and positive duration', () => {
  assert.equal(
    validGuideDestinations([
      { id: 'complete', place: 'Lisboa', timing: 'Maio', days: 4 },
    ]),
    true,
  );
  assert.equal(validGuideDestinations([{ place: '', timing: 'Maio', days: 4 }]), false);
  assert.equal(validGuideDestinations([{ place: 'Lisboa', timing: '', days: 4 }]), false);
  assert.equal(validGuideDestinations([{ place: 'Lisboa', timing: 'Maio', days: 0 }]), false);
});

test('child helpers derive submit names and ages from structured child records', () => {
  const children = [
    { id: 'a', name: 'Alice', age: '5' },
    { id: 'b', name: 'Antonio', age: 9 },
    { id: 'blank', name: ' ', age: '' },
  ];

  assert.deepEqual(validGuideChildren(children), [
    { id: 'a', name: 'Alice', age: 5 },
    { id: 'b', name: 'Antonio', age: 9 },
  ]);
  assert.deepEqual(deriveChildNames(children), ['Alice', 'Antonio']);
  assert.deepEqual(deriveChildAges(children), [5, 9]);
  assert.deepEqual(guideChildRecordsForSubmit(children), [
    { name: 'Alice', age: 5 },
    { name: 'Antonio', age: 9 },
  ]);
});

test('parseFreeformItineraryText returns complete structured destinations when text has order duration and timing', () => {
  assert.equal(typeof guideForm.parseFreeformItineraryText, 'function');
  const result = guideForm.parseFreeformItineraryText(
    'Primeiro Paris em julho de 2026 por 3 dias; depois Londres em agosto de 2026 por 2 dias.',
  );

  assert.equal(result.followUpQuestions.length, 0);
  assert.deepEqual(result.destinations, [
    {
      id: 'freeform-1',
      place: 'Paris',
      timing: 'julho de 2026',
      days: 3,
    },
    {
      id: 'freeform-2',
      place: 'Londres',
      timing: 'agosto de 2026',
      days: 2,
    },
  ]);
});

test('parseFreeformItineraryText asks duration follow-ups when days are missing', () => {
  assert.equal(typeof guideForm.parseFreeformItineraryText, 'function');
  const result = guideForm.parseFreeformItineraryText('Primeiro Paris em julho de 2026; depois Londres em agosto de 2026.');

  assert.deepEqual(result.destinations.map((destination) => destination.place), ['Paris', 'Londres']);
  assert.deepEqual(result.followUpQuestions, [
    {
      field: 'days',
      destinationId: 'freeform-1',
      message: 'Por quantos dias a família ficará em Paris?',
    },
    {
      field: 'days',
      destinationId: 'freeform-2',
      message: 'Por quantos dias a família ficará em Londres?',
    },
  ]);
});

test('parseFreeformItineraryText asks for order confirmation when multiple places are ambiguous', () => {
  assert.equal(typeof guideForm.parseFreeformItineraryText, 'function');
  const result = guideForm.parseFreeformItineraryText('Paris e Londres em julho de 2026 por 5 dias.');

  assert.deepEqual(result.destinations.map((destination) => destination.place), ['Paris', 'Londres']);
  assert.deepEqual(result.followUpQuestions, [
    {
      field: 'order',
      destinationId: null,
      message: 'Qual é a ordem correta dos destinos?',
    },
  ]);
});

test('normalizeRouteSuggestionDestinations returns editable canonical destinations', () => {
  assert.equal(typeof guideForm.normalizeRouteSuggestionDestinations, 'function');
  const destinations = guideForm.normalizeRouteSuggestionDestinations([
    { place: 'Paris, França', timing: 'Julho de 2026', days: 3 },
    { place: 'Londres', timing: 'depois de Paris', days: '2' },
  ]);

  assert.deepEqual(destinations, [
    { id: 'suggested-1', place: 'Paris, França', timing: 'Julho de 2026', days: 3 },
    { id: 'suggested-2', place: 'Londres', timing: 'depois de Paris', days: 2 },
  ]);
});

test('formatTripTiming produz exatamente o texto que vai impresso', () => {
  assert.equal(guideForm.formatTripTiming('Julho', 2026), 'Julho de 2026');
  assert.equal(guideForm.formatTripTiming('Março', '2027'), 'Março de 2027');
  // Sem mês ou com ano fora da faixa não existe texto: melhor vazio que errado.
  assert.equal(guideForm.formatTripTiming('', 2026), '');
  assert.equal(guideForm.formatTripTiming('Julho', 1999), '');
  assert.equal(guideForm.formatTripTiming('julho', 2026), '');
});

test('parseTripTiming recupera mês e ano de rascunhos antigos em texto livre', () => {
  assert.deepEqual(guideForm.parseTripTiming('Julho de 2026'), { month: 'Julho', year: 2026 });
  assert.deepEqual(guideForm.parseTripTiming('julho/2026'), { month: 'Julho', year: 2026 });
  assert.deepEqual(guideForm.parseTripTiming('marco de 2027'), { month: 'Março', year: 2027 });
  assert.deepEqual(guideForm.parseTripTiming('07/2026'), { month: 'Julho', year: 2026 });
  assert.deepEqual(guideForm.parseTripTiming('verão de 2026'), { month: '', year: 2026 });
  assert.deepEqual(guideForm.parseTripTiming('depois de Paris'), { month: '', year: 0 });
});

test('canonicalizeDestinationTiming esvazia o que não dá para imprimir', () => {
  const destinations = guideForm.canonicalizeDestinationTiming([
    { id: 'a', place: 'Paris', timing: 'julho de 2026', days: 3 },
    { id: 'b', place: 'Londres', timing: 'depois de Paris', days: 2 },
  ]);

  assert.equal(destinations[0].timing, 'Julho de 2026');
  assert.equal(destinations[1].timing, '');
  assert.equal(destinations[0].days, 3);
});

test('tripYearFromDestinations usa a primeira parada com ano reconhecido', () => {
  assert.equal(
    guideForm.tripYearFromDestinations([
      { place: 'Paris', timing: 'depois do carnaval', days: 2 },
      { place: 'Londres', timing: 'Agosto de 2027', days: 3 },
    ]),
    2027,
  );
  assert.equal(guideForm.tripYearFromDestinations([]), 0);
});

test('tripYearOptions cobre os próximos anos e mantém o já escolhido', () => {
  assert.deepEqual(guideForm.tripYearOptions(0, 2026), [2026, 2027, 2028, 2029]);
  assert.deepEqual(guideForm.tripYearOptions(2031, 2026), [2026, 2027, 2028, 2029, 2031]);
});

test('o perfil salvo guarda o ano de nascimento, não a idade que envelhece', () => {
  const form = {
    familyName: '  Família Lima  ',
    parents: [{ id: 'p1', name: ' Marina ' }],
    children: [{ id: 'c1', name: 'Aurora', age: 6 }],
  };

  const profile = guideForm.familyProfileFromForm(form, 2026);

  assert.equal(profile.familyName, 'Família Lima');
  assert.deepEqual(profile.parents, [{ id: 'p1', name: 'Marina' }]);
  assert.deepEqual(profile.children, [{ id: 'c1', name: 'Aurora', birth_year: 2020 }]);
});

test('carregar recalcula a idade para o ano desta viagem', () => {
  const profile = {
    family_name: 'Família Lima',
    parents: [{ id: 'p1', name: 'Marina' }],
    children: [{ id: 'c1', name: 'Aurora', birth_year: 2020 }],
  };

  // Mesma criança, duas viagens: a idade impressa acompanha o ano.
  assert.equal(guideForm.familyFormFromProfile(profile, 2026).children[0].age, 6);
  assert.equal(guideForm.familyFormFromProfile(profile, 2029).children[0].age, 9);
  assert.equal(guideForm.familyFormFromProfile(profile, 2026).familyName, 'Família Lima');
  assert.deepEqual(guideForm.familyFormFromProfile(profile, 2026).needingAgeReview, []);
});

test('idade fora da faixa do guia volta em branco em vez de ser recusada no fim', () => {
  const profile = {
    family_name: 'Família Lima',
    parents: [{ id: 'p1', name: 'Marina' }],
    children: [
      { id: 'c1', name: 'Aurora', birth_year: 2004 },
      { id: 'c2', name: 'Bento', birth_year: 2030 },
      { id: 'c3', name: 'Clara', birth_year: 2020 },
    ],
  };

  const form = guideForm.familyFormFromProfile(profile, 2026);

  // Já passou dos 17 e ainda não nasceu: as duas contas viram pedido de correção.
  assert.deepEqual(form.children.map((child) => child.age), ['', '', 6]);
  assert.deepEqual(form.needingAgeReview, ['Aurora', 'Bento']);
});

test('a conversão idade e ano de nascimento fecha nos dois sentidos', () => {
  for (let age = 1; age <= guideForm.MAX_GUIDE_CHILD_AGE; age += 1) {
    const born = guideForm.childBirthYear(age, 2027);
    assert.equal(guideForm.childAgeForTripYear(born, 2027), age);
  }
  assert.equal(guideForm.childBirthYear(0, 2027), 0);
  assert.equal(guideForm.childAgeForTripYear('', 2027), 0);
});
