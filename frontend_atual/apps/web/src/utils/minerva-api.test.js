import assert from 'node:assert/strict';
import test from 'node:test';

import authClient from '../lib/authClient.js';
import * as minervaApi from './minerva-api.js';
import {
  appendGuideLandmarks,
  appendGuideMetadata,
  buildDiscoverItineraryPayload,
  buildLandmarkMapsUrl,
  inferCatalogDestinationIds,
  mapParsedLandmarksToParsedData,
  mapRecommendationToParsedData,
  mappableLandmarks,
  splitQuickSuggestionLandmarks,
} from './minerva-api.js';

const catalog = {
  destinations: [
    {
      id: 'paris',
      city: 'Paris',
      country: 'Franca',
      landmarks: [],
    },
    {
      id: 'lisbon',
      city: 'Lisboa',
      country: 'Portugal',
      landmarks: [],
    },
    {
      id: 'london',
      city: 'Londres',
      country: 'Inglaterra',
      landmarks: [],
    },
    {
      id: 'cambridge',
      city: 'Cambridge',
      country: 'Inglaterra',
      landmarks: [],
    },
  ],
};

test('inferCatalogDestinationIds detects catalog cities in free text', () => {
  const ids = inferCatalogDestinationIds(
    'Vamos visitar Lisboa e depois Paris com as crianças.',
    catalog,
  );

  assert.deepEqual(ids, ['paris', 'lisbon']);
});

test('inferCatalogDestinationIds only matches country when it maps to one catalog destination', () => {
  assert.deepEqual(inferCatalogDestinationIds('Queremos ir para Portugal.', catalog), ['lisbon']);
  assert.deepEqual(inferCatalogDestinationIds('Queremos ir para Inglaterra.', catalog), []);
});

test('mapRecommendationToParsedData keeps day metadata and alternatives editable', () => {
  const data = mapRecommendationToParsedData(
    {
      selected_landmarks: ['lisbon:oceanario'],
      days: [
        {
          day: 1,
          title: 'Dia 1 em Lisboa',
          destination_ids: ['lisbon'],
          stops: [
            {
              selection_id: 'lisbon:oceanario',
              destination_id: 'lisbon',
              name: 'Oceanario',
              city: 'Lisboa',
              country: 'Portugal',
              description: ['Um aquario gigante.'],
              image: 'assets/oceanario.png',
              duration_minutes: 120,
              family_tip: 'Otimo para curiosos por animais.',
              match_reasons: ['Interesse da familia: animais.'],
              categories: ['animals'],
            },
          ],
        },
      ],
      alternatives: [
        {
          selection_id: 'lisbon:yellow-tram',
          destination_id: 'lisbon',
          name: 'Eletrico amarelo',
          city: 'Lisboa',
          country: 'Portugal',
          description: ['Um bondinho famoso.'],
          image: 'assets/tram.png',
          duration_minutes: 45,
          family_tip: 'Transforma deslocamento em passeio.',
          match_reasons: ['Bom ponto para apresentar a cidade as criancas.'],
          categories: ['rides'],
        },
      ],
    },
    catalog,
  );

  assert.deepEqual(data.selectedLandmarks, ['lisbon:oceanario']);
  assert.deepEqual(data.destinations, [{ id: 'lisbon', city: 'Lisboa', country: 'Portugal' }]);
  assert.equal(data.landmarks[0].id, 'lisbon:oceanario');
  assert.equal(data.landmarks[0].category, 'animals');
  assert.equal(minervaApi.categoryLabelForAttraction(data.landmarks[0]), 'Animais');
  assert.equal(data.landmarks[0].itinerary_day, 1);
  assert.equal(data.landmarks[0].is_catalog_landmark, true);
  assert.equal(data.landmarks[1].id, 'lisbon:yellow-tram');
  assert.equal(data.landmarks[1].category, 'rides');
  assert.equal(data.landmarks[1].is_alternative, true);
});

test('mapRecommendationToParsedData treats Google Places stops as custom landmarks', () => {
  const data = mapRecommendationToParsedData(
    {
      recommendation_source: 'google_places',
      selected_landmarks: ['google:abc123'],
      days: [
        {
          day: 1,
          title: 'Dia 1 em Roma',
          destination_ids: ['google-roma'],
          stops: [
            {
              selection_id: 'google:abc123',
              destination_id: 'google-roma',
              name: 'Coliseu',
              city: 'Roma',
              country: 'Italia',
              description: ['Um anfiteatro historico.'],
              image: null,
              image_attributions: [
                {
                  display_name: 'Maria Fotografa',
                  uri: 'https://example.com/maria',
                },
              ],
              google_maps_uri: 'https://maps.google.com/?cid=abc123',
              formatted_address: 'Piazza del Colosseo, Roma',
              latitude: 41.8902,
              longitude: 12.4922,
              duration_minutes: 90,
              family_tip: 'Procure os arcos gigantes.',
              match_reasons: ['Interesse da familia: historia.'],
              categories: ['history'],
              source_type: 'mentioned',
            },
          ],
        },
      ],
      alternatives: [],
    },
    catalog,
  );

  assert.deepEqual(data.destinations, [{ id: 'google-roma', city: 'Roma', country: 'Italia' }]);
  assert.equal(data.landmarks[0].id, 'google:abc123');
  assert.equal(data.landmarks[0].is_catalog_landmark, false);
  assert.equal(data.landmarks[0].google_maps_uri, 'https://maps.google.com/?cid=abc123');
  assert.equal(data.landmarks[0].maps_url, 'https://maps.google.com/?cid=abc123');
  assert.equal(data.landmarks[0].latitude, 41.8902);
  assert.equal(data.landmarks[0].longitude, 12.4922);
  assert.equal(data.landmarks[0].source_type, 'mentioned');
  assert.equal(data.landmarks[0].category, 'history');
  assert.deepEqual(data.landmarks[0].image_attributions, [
    {
      display_name: 'Maria Fotografa',
      uri: 'https://example.com/maria',
    },
  ]);
});

test('mapRecommendationToParsedData infers mentioned source from mandatory reason', () => {
  const data = mapRecommendationToParsedData(
    {
      recommendation_source: 'google_places',
      selected_landmarks: ['google:louvre'],
      days: [
        {
          day: 1,
          title: 'Dia 1 em Paris',
          destination_ids: ['google-paris'],
          stops: [
            {
              selection_id: 'google:louvre',
              destination_id: 'google-paris',
              name: 'Museu do Louvre',
              city: 'Paris',
              country: 'Franca',
              description: ['Ponto citado pela familia.'],
              match_reasons: ['Ponto obrigatorio informado pela familia.'],
              categories: ['museums'],
            },
            {
              selection_id: 'google:palais-decouverte',
              destination_id: 'google-paris',
              name: 'Palacio da descoberta',
              city: 'Paris',
              country: 'Franca',
              description: ['Sugestao educativa.'],
              match_reasons: ['Pedido da familia: educativo para criancas.'],
              categories: ['education'],
            },
          ],
        },
      ],
      alternatives: [],
    },
    catalog,
  );

  const sections = minervaApi.splitLandmarksBySource(data.landmarks);

  assert.deepEqual(sections.mentioned.map((item) => item.name), ['Museu do Louvre']);
  assert.deepEqual(sections.suggested.map((item) => item.name), ['Palacio da descoberta']);
});

test('splitLandmarksBySource separates user-mentioned places from suggestions', () => {
  const sections = minervaApi.splitLandmarksBySource([
    { id: 'eiffel', source_type: 'mentioned' },
    { id: 'park', source_type: 'suggested' },
    { id: 'museum', is_alternative: true },
  ]);

  assert.deepEqual(sections.mentioned.map((item) => item.id), ['eiffel']);
  assert.deepEqual(sections.suggested.map((item) => item.id), ['park', 'museum']);
});

test('defaultSelectedLandmarksForMode selects only mentioned places in quick mode when available', () => {
  const mapped = {
    selectedLandmarks: ['eiffel', 'park', 'museum'],
    landmarks: [
      { id: 'eiffel', source_type: 'mentioned' },
      { id: 'park', source_type: 'suggested' },
      { id: 'museum', source_type: 'suggested' },
    ],
  };

  assert.deepEqual(minervaApi.defaultSelectedLandmarksForMode(mapped, 'quick'), ['eiffel']);
  assert.deepEqual(minervaApi.defaultSelectedLandmarksForMode(mapped, 'itinerary'), [
    'eiffel',
    'park',
    'museum',
  ]);
});

test('buildLandmarkMapsUrl falls back to a Google Maps search query', () => {
  assert.equal(
    buildLandmarkMapsUrl({
      name: 'Torre Eiffel',
      city: 'Paris',
      country: 'Franca',
    }),
    'https://www.google.com/maps/search/?api=1&query=Torre%20Eiffel%20Paris%20Franca',
  );
});

test('mapParsedLandmarksToParsedData flattens manual landmarks without itinerary suggestions', () => {
  const data = mapParsedLandmarksToParsedData({
    selected_landmarks: ['custom-paris:torre-eiffel', 'custom-paris:louvre'],
    destinations: [
      {
        id: 'custom-paris',
        city: 'Paris',
        country: 'Franca',
        landmarks: [
          {
            id: 'torre-eiffel',
            selection_id: 'custom-paris:torre-eiffel',
            name: 'Torre Eiffel',
            description: ['Visita ja planejada pela familia.'],
            confidence: 0.94,
          },
          {
            id: 'louvre',
            selection_id: 'custom-paris:louvre',
            name: 'Louvre',
            description: ['Museu citado no roteiro.'],
            confidence: 0.88,
          },
        ],
      },
    ],
  });

  assert.deepEqual(data.destinations, [{ id: 'custom-paris', city: 'Paris', country: 'Franca' }]);
  assert.deepEqual(data.selectedLandmarks, ['custom-paris:torre-eiffel', 'custom-paris:louvre']);
  assert.equal(data.landmarks[0].id, 'custom-paris:torre-eiffel');
  assert.equal(data.landmarks[0].destination_id, 'custom-paris');
  assert.equal(data.landmarks[0].is_catalog_landmark, false);
  assert.equal(data.landmarks[0].itinerary_day, null);
  assert.equal(data.landmarks[0].description, 'Visita ja planejada pela familia.');
  assert.equal(
    data.landmarks[0].maps_url,
    'https://www.google.com/maps/search/?api=1&query=Torre%20Eiffel%20Paris%20Franca',
  );
});

test('splitQuickSuggestionLandmarks separates primary cards from alternatives', () => {
  const sections = splitQuickSuggestionLandmarks([
    { id: 'primary-1', is_alternative: false },
    { id: 'alternative-1', is_alternative: true },
    { id: 'primary-2' },
  ]);

  assert.deepEqual(sections.primary.map((item) => item.id), ['primary-1', 'primary-2']);
  assert.deepEqual(sections.alternatives.map((item) => item.id), ['alternative-1']);
});

test('mappableLandmarks keeps only landmarks with numeric coordinates', () => {
  const items = mappableLandmarks([
    { id: 'with-number', latitude: 48.8566, longitude: 2.3522 },
    { id: 'with-string', latitude: '41.8902', longitude: '12.4922' },
    { id: 'missing-latitude', longitude: 12.4922 },
    { id: 'invalid', latitude: 'x', longitude: 12.4922 },
  ]);

  assert.deepEqual(items.map((item) => item.id), ['with-number', 'with-string']);
  assert.equal(items[1].latitude, 41.8902);
  assert.equal(items[1].longitude, 12.4922);
});

test('hasMappableCoordinates accepts only complete numeric coordinates', () => {
  assert.equal(typeof minervaApi.hasMappableCoordinates, 'function');
  assert.equal(minervaApi.hasMappableCoordinates({ latitude: 48.8566, longitude: 2.3522 }), true);
  assert.equal(minervaApi.hasMappableCoordinates({ latitude: '41.8902', longitude: '12.4922' }), true);
  assert.equal(minervaApi.hasMappableCoordinates({ latitude: 48.8566 }), false);
  assert.equal(minervaApi.hasMappableCoordinates({ latitude: 'abc', longitude: 2.3522 }), false);
});

test('landmarkMapAction chooses embedded map when coordinates exist and external fallback otherwise', () => {
  assert.deepEqual(
    minervaApi.landmarkMapAction({
      name: 'Torre Eiffel',
      city: 'Paris',
      country: 'Franca',
      latitude: 48.8584,
      longitude: 2.2945,
    }),
    {
      mode: 'embedded',
      mapsUrl: 'https://www.google.com/maps/search/?api=1&query=Torre%20Eiffel%20Paris%20Franca',
    },
  );
  assert.deepEqual(
    minervaApi.landmarkMapAction({
      name: 'Louvre',
      city: 'Paris',
      country: 'Franca',
    }),
    {
      mode: 'external',
      mapsUrl: 'https://www.google.com/maps/search/?api=1&query=Louvre%20Paris%20Franca',
    },
  );
});

test('tripMapExplorerItems orders selected landmarks first and labels status', () => {
  const items = minervaApi.tripMapExplorerItems(
    [
      { id: 'suggested-1', name: 'Jardim', latitude: 1, longitude: 1, is_alternative: true },
      { id: 'selected-1', name: 'Museu', latitude: 2, longitude: 2 },
      { id: 'missing-coordinates', name: 'Sem mapa' },
    ],
    ['selected-1'],
  );

  assert.deepEqual(items.map((item) => item.id), ['selected-1', 'suggested-1']);
  assert.deepEqual(items.map((item) => item.map_status), ['selected', 'suggested']);
});

test('tripMapVisibleItems hides suggested map points by default and can include them', () => {
  const landmarks = [
    { id: 'selected-1', name: 'Museu', latitude: 2, longitude: 2 },
    { id: 'suggested-1', name: 'Jardim', latitude: 1, longitude: 1 },
    { id: 'missing-coordinates', name: 'Sem mapa' },
  ];

  assert.deepEqual(
    minervaApi.tripMapVisibleItems(landmarks, ['selected-1']).map((item) => item.id),
    ['selected-1'],
  );
  assert.deepEqual(
    minervaApi.tripMapVisibleItems(landmarks, ['selected-1'], true).map((item) => item.id),
    ['selected-1', 'suggested-1'],
  );
});

test('missingSelectedMapLandmarks reports selected places without coordinates', () => {
  const landmarks = [
    { id: 'with-map', name: 'Com mapa', latitude: 1, longitude: 2 },
    { id: 'missing-map', name: 'Sem mapa' },
    { id: 'suggested-missing', name: 'Sugestao sem mapa' },
  ];

  assert.deepEqual(
    minervaApi.missingSelectedMapLandmarks(landmarks, ['with-map', 'missing-map'])
      .map((item) => item.id),
    ['missing-map'],
  );
});

test('mergeResolvedLandmarkLocations enriches current cards without dropping suggestions', () => {
  const currentLandmarks = [
    {
      id: 'custom-paris:torre-eiffel',
      name: 'Torre Eiffel',
      city: 'Paris',
      country: 'Franca',
    },
    {
      id: 'google:park',
      name: 'Parque sugerido',
      source_type: 'suggested',
      latitude: 48.86,
      longitude: 2.33,
    },
  ];
  const resolvedLandmarks = [
    {
      id: 'custom-paris:torre-eiffel',
      name: 'Torre Eiffel',
      city: 'Paris',
      country: 'Franca',
      latitude: 48.8584,
      longitude: 2.2945,
      google_maps_uri: 'https://maps.google.com/?cid=eiffel',
      formatted_address: 'Paris',
    },
  ];

  const merged = minervaApi.mergeResolvedLandmarkLocations(currentLandmarks, resolvedLandmarks);

  assert.equal(merged.length, 2);
  assert.equal(merged[0].latitude, 48.8584);
  assert.equal(merged[0].longitude, 2.2945);
  assert.equal(merged[0].maps_url, 'https://maps.google.com/?cid=eiffel');
  assert.equal(merged[1].id, 'google:park');
});

test('mergeLandmarkSuggestions keeps existing order and appends only new suggestions', () => {
  const landmarks = minervaApi.mergeLandmarkSuggestions(
    [
      { id: 'selected-1', name: 'Museu' },
      { id: 'suggested-1', name: 'Jardim antigo' },
    ],
    [
      { id: 'suggested-1', name: 'Jardim novo' },
      { id: 'suggested-2', name: 'Parque' },
    ],
  );

  assert.deepEqual(landmarks.map((item) => item.id), ['selected-1', 'suggested-1', 'suggested-2']);
  assert.equal(landmarks[1].name, 'Jardim antigo');
});

test('mergeDestinationSuggestions keeps existing destinations and appends new ones', () => {
  const destinations = minervaApi.mergeDestinationSuggestions(
    [
      { id: 'paris', city: 'Paris' },
      { id: 'versailles', city: 'Versalhes' },
    ],
    [
      { id: 'paris', city: 'Paris atualizada' },
      { id: 'giverny', city: 'Giverny' },
    ],
  );

  assert.deepEqual(destinations.map((item) => item.id), ['paris', 'versailles', 'giverny']);
  assert.equal(destinations[0].city, 'Paris');
});

test('appendGuideLandmarks sends catalog ids and custom fallback separately', () => {
  const formData = new FormData();

  appendGuideLandmarks(formData, {
    landmarks: [
      {
        id: 'lisbon:oceanario',
        is_catalog_landmark: true,
        name: 'Oceanario',
        city: 'Lisboa',
        country: 'Portugal',
      },
      {
        id: 'custom-rome:colosseum',
        is_catalog_landmark: false,
        name: 'Colosseum',
        city: 'Rome',
        country: 'Italy',
        image: 'https://lh3.googleusercontent.com/colosseum=w900',
        image_attributions: [
          { display_name: 'Google Photographer', uri: 'https://maps.google.com/contrib' },
        ],
      },
    ],
  });

  assert.deepEqual(formData.getAll('selected_landmarks'), ['lisbon:oceanario']);
  assert.equal(
    formData.get('custom_landmarks'),
    JSON.stringify([
      {
        name: 'Colosseum',
        city: 'Rome',
        country: 'Italy',
        description: [],
        image: 'https://lh3.googleusercontent.com/colosseum=w900',
        image_attributions: [
          { display_name: 'Google Photographer', uri: 'https://maps.google.com/contrib' },
        ],
      },
    ]),
  );
});

test('selectGuideLandmarks preserves only selected attractions in guide order', () => {
  const landmarks = [
    { id: 'suggested-park', name: 'Parque sugerido' },
    { id: 'selected-museum', name: 'Museu selecionado' },
    { id: 'selected-square', name: 'Praca selecionada' },
  ];

  assert.deepEqual(
    minervaApi.selectGuideLandmarks(landmarks, ['selected-square', 'selected-museum'])
      .map((item) => item.id),
    ['selected-square', 'selected-museum'],
  );
});

test('appendGuideLandmarks filters unselected attraction suggestions from payload', () => {
  const formData = new FormData();

  appendGuideLandmarks(formData, {
    selectedLandmarks: ['selected-catalog', 'selected-custom'],
    landmarks: [
      {
        id: 'selected-catalog',
        is_catalog_landmark: true,
        name: 'Museu selecionado',
        city: 'Lisboa',
        country: 'Portugal',
      },
      {
        id: 'unselected-catalog',
        is_catalog_landmark: true,
        name: 'Parque sugerido',
        city: 'Lisboa',
        country: 'Portugal',
      },
      {
        id: 'selected-custom',
        is_catalog_landmark: false,
        name: 'Loja local selecionada',
        city: 'Lisboa',
        country: 'Portugal',
      },
      {
        id: 'unselected-custom',
        is_catalog_landmark: false,
        name: 'Teatro sugerido',
        city: 'Lisboa',
        country: 'Portugal',
      },
    ],
  });

  assert.deepEqual(formData.getAll('selected_landmarks'), ['selected-catalog']);
  assert.equal(
    formData.get('custom_landmarks'),
    JSON.stringify([
      {
        name: 'Loja local selecionada',
        city: 'Lisboa',
        country: 'Portugal',
        description: [],
      },
    ]),
  );
});

test('buildDiscoverItineraryPayload includes structured destinations preferences and child ages', () => {
  const payload = buildDiscoverItineraryPayload({
    destinationsList: [
      { id: 'paris', place: 'Paris, França', timing: 'Julho de 2026', days: 3 },
      { id: 'london', place: 'Londres', timing: 'depois de Paris', days: 2 },
    ],
    itineraryPreferences: {
      pace: 'light',
      interests: ['museus', 'parques'],
    },
    childrenList: [
      { name: 'Alice', age: 5 },
      { name: 'Antonio', age: 9 },
    ],
  });

  assert.equal(
    payload.destination,
    'Destino 1: Paris, França; quando: Julho de 2026; duração: 3 dias.\nDestino 2: Londres; quando: depois de Paris; duração: 2 dias.',
  );
  assert.equal(payload.days, 5);
  assert.equal(payload.pace, 'light');
  assert.deepEqual(payload.interests, ['museus', 'parques']);
  assert.deepEqual(payload.children_ages, [5, 9]);
  assert.deepEqual(payload.structured_destinations, [
    { id: 'paris', place: 'Paris, França', timing: 'Julho de 2026', days: 3 },
    { id: 'london', place: 'Londres', timing: 'depois de Paris', days: 2 },
  ]);
});

test('buildStructuredLandmarksPayload keeps only destinations with place and landmarks', () => {
  const payload = minervaApi.buildStructuredLandmarksPayload({
    destinationsList: [
      {
        id: 'paris',
        place: 'Paris, França',
        timing: 'Julho de 2026',
        days: 3,
        landmarks: [' Torre Eiffel ', '', 'Museu do Louvre'],
      },
      { id: 'sem-pontos', place: 'Londres', timing: 'depois', days: 2, landmarks: ['  '] },
      { id: 'sem-lugar', place: '', timing: '', days: 1, landmarks: ['Coliseu'] },
    ],
  });

  assert.deepEqual(payload, {
    destinations: [
      { place: 'Paris, França', landmarks: ['Torre Eiffel', 'Museu do Louvre'] },
    ],
  });
});

test('buildRouteSuggestionPayload sends freeform constraints and current structured destinations', () => {
  assert.equal(typeof minervaApi.buildRouteSuggestionPayload, 'function');
  const payload = minervaApi.buildRouteSuggestionPayload({
    tripIdea: 'Queremos Paris e Londres com parques.',
    destinationsList: [
      { id: 'paris', place: 'Paris, França', timing: 'Julho de 2026', days: 3 },
    ],
    itineraryPreferences: {
      days: 5,
      pace: 'light',
      interests: ['parques', 'museus'],
    },
    childrenList: [{ name: 'Alice', age: 6 }],
  });

  assert.deepEqual(payload, {
    trip_idea: 'Queremos Paris e Londres com parques.',
    days: 5,
    pace: 'light',
    interests: ['parques', 'museus'],
    children_ages: [6],
    structured_destinations: [
      { id: 'paris', place: 'Paris, França', timing: 'Julho de 2026', days: 3 },
    ],
  });
});

test('appendGuideMetadata preserves family cover count with child ages for PDF generation', () => {
  const formData = new FormData();

  appendGuideMetadata(formData, {
    title: 'Família Silva',
    childrenNames: 'Alice, Antonio',
    childrenAges: [5, 9],
    parentsNames: 'Ana, Otavio',
    year: 2026,
    expectedVisibleFamilyMemberCount: 4,
  });

  assert.equal(formData.get('title'), 'Família Silva');
  assert.equal(formData.get('children_names'), 'Alice, Antonio');
  assert.deepEqual(formData.getAll('children_ages'), ['5', '9']);
  assert.equal(formData.get('parents_names'), 'Ana, Otavio');
  assert.equal(formData.get('year'), '2026');
  assert.equal(formData.get('expected_visible_family_member_count'), '4');
});

test('appendGuideMetadata sends versioned photo-processing consent', () => {
  const formData = new FormData();

  appendGuideMetadata(formData, {
    title: 'Guia da Família',
    photoProcessingConsent: true,
    privacyConsentVersion: '2026-07-09',
    privacyConsentAt: '2026-07-09T18:30:00.000Z',
  });

  assert.equal(formData.get('photo_processing_consent'), 'true');
  assert.equal(formData.get('privacy_consent_version'), '2026-07-09');
  assert.equal(formData.get('privacy_consent_at'), '2026-07-09T18:30:00.000Z');
});

test('buildGuideItineraryPayload preserves destinations preferences and reviewed days', () => {
  const itinerary = minervaApi.buildGuideItineraryPayload({
    itineraryMode: 'freeform',
    destinationsList: [
      {
        id: 'paris',
        place: 'Paris, França',
        timing: 'Julho de 2026',
        days: 3,
        landmarks: ['Torre Eiffel'],
      },
    ],
    itineraryPreferences: {
      pace: 'light',
      interests: ['museus', 'parques'],
    },
    recommendedDays: [
      {
        day: 1,
        title: 'Primeiro dia em Paris',
        theme: 'Ícones da cidade',
        landmarks: [
          {
            id: 'paris:eiffel-tower',
            name: 'Torre Eiffel',
            destination_id: 'paris',
          },
        ],
      },
    ],
    extraLandmarks: [
      {
        id: 'paris:louvre',
        name: 'Museu do Louvre',
        destination_id: 'paris',
      },
    ],
  });

  assert.deepEqual(itinerary, {
    mode: 'freeform',
    pace: 'light',
    interests: ['museus', 'parques'],
    destinations: [
      {
        id: 'paris',
        place: 'Paris, França',
        timing: 'Julho de 2026',
        days: 3,
        order: 1,
      },
    ],
    days: [
      {
        day: 1,
        title: 'Primeiro dia em Paris',
        theme: 'Ícones da cidade',
        stops: [
          {
            selection_id: 'paris:eiffel-tower',
            name: 'Torre Eiffel',
            destination_id: 'paris',
          },
        ],
      },
    ],
    unplanned_stops: [
      {
        selection_id: 'paris:louvre',
        name: 'Museu do Louvre',
        destination_id: 'paris',
      },
    ],
  });
});

test('appendGuideMetadata serializes the itinerary reviewed by the family', () => {
  const formData = new FormData();
  const itinerary = {
    mode: 'known',
    pace: 'balanced',
    interests: [],
    destinations: [
      {
        id: 'lisbon',
        place: 'Lisboa, Portugal',
        timing: 'Agosto de 2026',
        days: 2,
        order: 1,
      },
    ],
    days: [],
    unplanned_stops: [],
  };

  appendGuideMetadata(formData, {
    title: 'Família Silva',
    childrenNames: 'Alice',
    parentsNames: 'Ana',
    year: 2026,
    itinerary,
  });

  assert.deepEqual(JSON.parse(formData.get('itinerary_json')), itinerary);
});

test('restaurant recommendations extra is explicit about the no-charge pilot contract', () => {
  assert.equal(minervaApi.RESTAURANT_RECOMMENDATIONS_EXTRA.id, 'restaurant_recommendations_extra');
  assert.equal(minervaApi.RESTAURANT_RECOMMENDATIONS_EXTRA.price_cents, 0);
  assert.equal(minervaApi.RESTAURANT_RECOMMENDATIONS_EXTRA.price_label, 'Incluído no piloto');
});

test('generatePDF sends the same caller-owned idempotency key with the authenticated request', async () => {
  const originalFetch = globalThis.fetch;
  let capturedOptions;
  await authClient.signup('idempotency-owner@example.com', 'Senha123', 'Família Silva');
  await authClient.login('idempotency-owner@example.com', 'Senha123');
  globalThis.fetch = async (_url, options = {}) => {
    capturedOptions = options;
    return new Response(JSON.stringify({ download_url: '/download/guide.pdf' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    await minervaApi.generatePDF({
      title: 'Família Silva',
      childrenNames: 'Alice',
      parentsNames: 'Ana',
      year: 2026,
      familyPhoto: new Blob(['photo'], { type: 'image/png' }),
      selectedLandmarks: ['paris:eiffel-tower'],
    }, { idempotencyKey: 'guide-stable-retry-key' });

    assert.equal(capturedOptions.headers.get('Idempotency-Key'), 'guide-stable-retry-key');
    assert.equal(capturedOptions.headers.get('Authorization'), 'Bearer local-development-token');
  } finally {
    globalThis.fetch = originalFetch;
    await authClient.logout();
  }
});

test('waitForGuideJob polls an owner-scoped job until its durable result is ready', async () => {
  const originalFetch = globalThis.fetch;
  const seen = [];
  await authClient.signup('job-owner@example.com', 'Senha123', 'Família Silva');
  await authClient.login('job-owner@example.com', 'Senha123');
  globalThis.fetch = async (url, options = {}) => {
    seen.push({ url: String(url), options });
    const payload = seen.length === 1
      ? { id: 'job-123', status: 'running', stage: 'rendering_pdf', progress: 75 }
      : {
        id: 'job-123',
        status: 'succeeded',
        stage: 'complete',
        progress: 100,
        result: { download_url: '/download/guide.pdf', filename: 'guide.pdf' },
      };
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  const updates = [];

  try {
    const result = await minervaApi.waitForGuideJob('job-123', {
      intervalMs: 0,
      sleep: async () => {},
      onUpdate: (job) => updates.push([job.stage, job.progress]),
    });

    assert.deepEqual(result, { download_url: '/download/guide.pdf', filename: 'guide.pdf' });
    assert.deepEqual(updates, [['rendering_pdf', 75], ['complete', 100]]);
    assert.deepEqual(seen.map(({ url }) => new URL(url).pathname), ['/api/jobs/job-123', '/api/jobs/job-123']);
    seen.forEach(({ options }) => {
      assert.equal(options.headers.get('Authorization'), 'Bearer local-development-token');
    });
  } finally {
    globalThis.fetch = originalFetch;
    await authClient.logout();
  }
});

test('appendGuideMetadata sends restaurant extra entitlement only when selected', () => {
  const baseFormData = new FormData();
  appendGuideMetadata(baseFormData, {
    title: 'Família Silva',
    childrenNames: 'Alice',
    parentsNames: 'Ana',
    year: 2026,
  });

  const extraFormData = new FormData();
  appendGuideMetadata(extraFormData, {
    title: 'Família Silva',
    childrenNames: 'Alice',
    parentsNames: 'Ana',
    year: 2026,
    restaurantRecommendationsExtra: true,
  });

  assert.equal(baseFormData.get('restaurant_recommendations_extra'), null);
  assert.equal(extraFormData.get('restaurant_recommendations_extra'), 'true');
});

test('guide library APIs list, read, delete and download through authenticated owner routes', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  const guide = {
    id: 'guide-123',
    title: 'Família Silva em Lisboa',
    status: 'succeeded',
    created_at: '2026-07-09T12:00:00+00:00',
    updated_at: '2026-07-09T12:00:00+00:00',
    expires_at: '2026-08-08T12:00:00+00:00',
    cover_fallback_used: false,
    destinations: [{ id: 'lisbon', place: 'Lisboa, Portugal' }],
    download_url: '/download/guide-123.pdf',
  };

  await authClient.signup('dashboard-owner@example.com', 'Senha123', 'Família Silva');
  await authClient.login('dashboard-owner@example.com', 'Senha123');

  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    const method = options.method || 'GET';

    if (String(url).endsWith('/api/guides') && method === 'GET') {
      return new Response(JSON.stringify({ guides: [guide] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (String(url).endsWith('/api/guides/guide-123') && method === 'GET') {
      return new Response(JSON.stringify(guide), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (String(url).endsWith('/api/guides/guide-123') && method === 'DELETE') {
      return new Response(JSON.stringify({ deleted: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (String(url).endsWith('/download/guide-123.pdf') && method === 'GET') {
      return new Response('%PDF-test', {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="familia-silva.pdf"',
        },
      });
    }
    return new Response(null, { status: 404 });
  };

  try {
    assert.deepEqual(await minervaApi.listGuides(), [guide]);
    assert.deepEqual(await minervaApi.getGuide('guide-123'), guide);
    assert.equal(await minervaApi.deleteGuide('guide-123'), true);
    const download = await minervaApi.downloadGuidePdf(guide.download_url);

    assert.equal(await download.blob.text(), '%PDF-test');
    assert.equal(download.filename, 'familia-silva.pdf');
    assert.deepEqual(
      calls.map(({ url, options }) => [new URL(url).pathname, options.method || 'GET']),
      [
        ['/api/guides', 'GET'],
        ['/api/guides/guide-123', 'GET'],
        ['/api/guides/guide-123', 'DELETE'],
        ['/download/guide-123.pdf', 'GET'],
      ],
    );
    calls.forEach(({ options }) => {
      assert.equal(options.headers.get('Authorization'), 'Bearer local-development-token');
    });
  } finally {
    globalThis.fetch = originalFetch;
    await authClient.logout();
  }
});

test('guide draft APIs restore, save and discard through authenticated owner routes', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  const draft = {
    id: 'draft-123',
    title: 'Rascunho de guia',
    payload: { current_step: 3, family_name: 'Silva' },
    revision: 2,
    status: 'active',
  };

  await authClient.signup('draft-owner@example.com', 'Senha123', 'Família Rascunho');
  await authClient.login('draft-owner@example.com', 'Senha123');
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    const method = options.method || 'GET';
    if (String(url).endsWith('/api/drafts/current') && method === 'GET') {
      return new Response(JSON.stringify({ draft }), { status: 200 });
    }
    if (String(url).endsWith('/api/drafts') && method === 'POST') {
      return new Response(JSON.stringify({ ...draft, id: 'draft-created', revision: 1 }), { status: 201 });
    }
    if (String(url).endsWith('/api/drafts/draft-123') && method === 'PUT') {
      return new Response(JSON.stringify(draft), { status: 200 });
    }
    if (String(url).endsWith('/api/drafts/draft-123') && method === 'DELETE') {
      return new Response(JSON.stringify({ deleted: true }), { status: 200 });
    }
    return new Response(null, { status: 404 });
  };

  try {
    assert.deepEqual(await minervaApi.getCurrentGuideDraft(), draft);
    const created = await minervaApi.createGuideDraft({ title: draft.title, payload: draft.payload });
    assert.equal(created.id, 'draft-created');
    assert.deepEqual(
      await minervaApi.updateGuideDraft(draft.id, {
        title: draft.title,
        payload: draft.payload,
        revision: 1,
      }),
      draft,
    );
    assert.equal(await minervaApi.discardGuideDraft(draft.id), true);
    assert.deepEqual(
      calls.map(({ url, options }) => [new URL(url).pathname, options.method || 'GET']),
      [
        ['/api/drafts/current', 'GET'],
        ['/api/drafts', 'POST'],
        ['/api/drafts/draft-123', 'PUT'],
        ['/api/drafts/draft-123', 'DELETE'],
      ],
    );
    calls.forEach(({ options }) => {
      assert.equal(options.headers.get('Authorization'), 'Bearer local-development-token');
    });
  } finally {
    globalThis.fetch = originalFetch;
    await authClient.logout();
  }
});

test('guide download rejects external URLs before sending the owner token', async () => {
  await assert.rejects(
    () => minervaApi.downloadGuidePdf('https://malicious.example/guide.pdf'),
    /Link de download inválido/,
  );
});
