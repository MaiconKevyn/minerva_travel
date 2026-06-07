import assert from 'node:assert/strict';
import test from 'node:test';

import * as minervaApi from './minerva-api.js';
import {
  appendGuideLandmarks,
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
  assert.equal(data.landmarks[0].itinerary_day, 1);
  assert.equal(data.landmarks[0].is_catalog_landmark, true);
  assert.equal(data.landmarks[1].id, 'lisbon:yellow-tram');
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
  assert.deepEqual(data.landmarks[0].image_attributions, [
    {
      display_name: 'Maria Fotografa',
      uri: 'https://example.com/maria',
    },
  ]);
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
      },
    ]),
  );
});
