
import {
  deriveChildAges,
  normalizeGuideDestinations,
  serializeGuideDestinations,
  totalTripDays,
} from './guide-form.js';
import { authenticatedFetch } from '../lib/authFetch.js';
import { normalizeLandmarkActivitySelections } from './landmark-activities.js';

export { authorizationHeaders } from '../lib/authFetch.js';

const DEFAULT_API_BASE_URL = 'https://minerva-travel.onrender.com';

export const apiBaseUrl = () => import.meta.env?.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;

export const RESTAURANT_RECOMMENDATIONS_EXTRA = {
  id: 'restaurant_recommendations_extra',
  label: 'Recomendações de restaurantes para a família',
  description: 'Sugestões de restaurantes próximos aos locais selecionados, incluídas no piloto.',
  price_cents: 0,
  currency: 'BRL',
  price_label: 'Incluído no piloto',
};

export const createIdempotencyKey = () => {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return `guide-${globalThis.crypto.randomUUID()}`;
  }
  return `guide-${Date.now()}-${Math.random().toString(36).slice(2, 14)}`;
};

export const ATTRACTION_CATEGORY_LABELS = {
  animals: 'Animais',
  architecture: 'Arquitetura',
  art: 'Arte',
  education: 'Educativo',
  family: 'Família',
  food: 'Comida',
  history: 'História',
  icons: 'Ícones',
  local_stores: 'Lojas locais',
  museums: 'Museus',
  outdoor: 'Ao ar livre',
  parks: 'Parques',
  play: 'Brincadeiras',
  rides: 'Passeios',
  river: 'Rio e passeios',
  science: 'Ciência',
  shopping: 'Compras',
  squares: 'Praças',
  theaters: 'Teatros',
  views: 'Vistas',
};

export const normalizeTextForMatching = (value) =>
  String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

export const inferCatalogDestinationIds = (message, catalog) => {
  const destinations = catalog?.destinations || [];
  const text = normalizeTextForMatching(message);
  const countryCounts = destinations.reduce((acc, destination) => {
    const country = normalizeTextForMatching(destination.country);
    acc[country] = (acc[country] || 0) + 1;
    return acc;
  }, {});

  return destinations
    .filter((destination) => {
      const city = normalizeTextForMatching(destination.city);
      const country = normalizeTextForMatching(destination.country);
      const displayTitle = normalizeTextForMatching(destination.display_title);
      return (
        (city && text.includes(city)) ||
        (displayTitle && text.includes(displayTitle)) ||
        (country && countryCounts[country] === 1 && text.includes(country))
      );
    })
    .map((destination) => destination.id);
};

const uniqueById = (items) => {
  const seen = new Set();
  return items.filter((item) => {
    if (!item?.id || seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
};

export const buildLandmarkMapsUrl = (landmark = {}) => {
  if (landmark.google_maps_uri) {
    return landmark.google_maps_uri;
  }
  const query = [landmark.name, landmark.city, landmark.country]
    .filter(Boolean)
    .join(' ')
    .trim();
  if (!query) {
    return '';
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
};

const hasMandatoryMentionReason = (item = {}) =>
  (item.match_reasons || []).some((reason) => {
    const normalized = normalizeTextForMatching(reason);
    return normalized.includes('ponto obrigatorio') || normalized.includes('informado pela familia');
  });

const normalizeSourceType = (value, item = {}) =>
  value === 'mentioned' || hasMandatoryMentionReason(item) ? 'mentioned' : 'suggested';

export const primaryAttractionCategory = (item = {}) =>
  item.category || item.categories?.[0] || 'family';

export const categoryLabelForAttraction = (item = {}) => {
  const category = typeof item === 'string' ? item : primaryAttractionCategory(item);
  return ATTRACTION_CATEGORY_LABELS[category] || category;
};

export const filterAttractionsByCategory = (landmarks = [], category = 'all') => {
  if (!category || category === 'all') {
    return landmarks;
  }
  return landmarks.filter((landmark) => {
    const categories = landmark.categories?.length
      ? landmark.categories
      : [primaryAttractionCategory(landmark)];
    return categories.includes(category);
  });
};

const mapStopToLandmark = (stop, day = null, isAlternative = false, isCatalogLandmark = true) => ({
  id: stop.selection_id,
  selection_id: stop.selection_id,
  name: stop.name,
  city: stop.city,
  country: stop.country,
  confidence: stop.match_score ? Math.min(stop.match_score / 250, 1) : 0.85,
  description: Array.isArray(stop.description) ? stop.description[0] : (stop.description || ''),
  description_paragraphs: Array.isArray(stop.description) ? stop.description : [stop.description].filter(Boolean),
  image: stop.image,
  image_attributions: stop.image_attributions || [],
  google_maps_uri: stop.google_maps_uri || '',
  formatted_address: stop.formatted_address || '',
  maps_url: buildLandmarkMapsUrl(stop),
  latitude: stop.latitude,
  longitude: stop.longitude,
  destination_id: stop.destination_id,
  duration_minutes: stop.duration_minutes,
  family_tip: stop.family_tip,
  match_reasons: stop.match_reasons || [],
  source_type: normalizeSourceType(stop.source_type, stop),
  category: primaryAttractionCategory(stop),
  categories: stop.categories || [],
  itinerary_day: day?.day || null,
  itinerary_title: day?.title || '',
  itinerary_theme: day?.theme || '',
  is_catalog_landmark: isCatalogLandmark,
  is_alternative: isAlternative,
});

export const mapRecommendationToParsedData = (recommendation, catalog) => {
  const isCatalogRecommendation = recommendation?.recommendation_source !== 'google_places';
  const stops = (recommendation?.days || []).flatMap((day) =>
    (day.stops || []).map((stop) => mapStopToLandmark(stop, day, false, isCatalogRecommendation))
  );
  const alternatives = (recommendation?.alternatives || []).map((stop) =>
    mapStopToLandmark(stop, null, true, isCatalogRecommendation)
  );
  const landmarksByDestinationId = [...stops, ...alternatives].reduce((acc, landmark) => {
    if (!acc[landmark.destination_id]) {
      acc[landmark.destination_id] = landmark;
    }
    return acc;
  }, {});
  const destinationIds = [
    ...new Set([
      ...stops.map((stop) => stop.destination_id),
      ...alternatives.map((stop) => stop.destination_id),
    ]),
  ];
  const destinations = destinationIds.map((destinationId) => {
    const destination = (catalog?.destinations || []).find((item) => item.id === destinationId);
    const landmark = landmarksByDestinationId[destinationId];
    return {
      id: destinationId,
      city: destination?.city || landmark?.city || destinationId,
      country: destination?.country || landmark?.country || '',
    };
  });

  return {
    destinations,
    landmarks: uniqueById([...stops, ...alternatives]),
    selectedLandmarks: recommendation?.selected_landmarks || [],
  };
};

const mapManualLandmark = (landmark, destination = {}) => {
  const selectionId = landmark.selection_id || landmark.id;
  const descriptionParagraphs = Array.isArray(landmark.description)
    ? landmark.description
    : [landmark.description].filter(Boolean);
  const image = typeof landmark.image === 'string'
    ? landmark.image
    : landmark.image?.image_url || null;

  return {
    ...landmark,
    id: selectionId,
    selection_id: selectionId,
    landmark_id: landmark.id,
    name: landmark.name,
    city: landmark.city || destination.city || '',
    country: landmark.country || destination.country || '',
    confidence: landmark.confidence || 0.85,
    description: descriptionParagraphs[0] || '',
    description_paragraphs: descriptionParagraphs,
    image,
    image_attributions: landmark.image_attributions || [],
    google_maps_uri: landmark.google_maps_uri || '',
    formatted_address: landmark.formatted_address || '',
    maps_url: buildLandmarkMapsUrl({ ...landmark, city: landmark.city || destination.city, country: landmark.country || destination.country }),
    latitude: landmark.latitude,
    longitude: landmark.longitude,
    destination_id: landmark.destination_id || destination.id,
    duration_minutes: landmark.duration_minutes || null,
    family_tip: landmark.family_tip || null,
    match_reasons: landmark.match_reasons || [],
    source_type: normalizeSourceType(landmark.source_type || 'mentioned', landmark),
    category: primaryAttractionCategory(landmark),
    categories: landmark.categories || [],
    itinerary_day: null,
    itinerary_title: '',
    itinerary_theme: '',
    is_catalog_landmark: false,
    is_alternative: false,
  };
};

export const mapParsedLandmarksToParsedData = (data) => {
  const destinations = (data?.destinations || []).map((destination) => ({
    ...destination,
    id: destination.id,
    city: destination.city || '',
    country: destination.country || '',
  }));
  const nestedLandmarks = destinations.flatMap((destination) =>
    (destination.landmarks || []).map((landmark) => mapManualLandmark(landmark, destination))
  );
  const flatLandmarks = (data?.landmarks || []).map((landmark) => {
    const destination = destinations.find((item) => item.id === landmark.destination_id) || {};
    return mapManualLandmark(landmark, destination);
  });
  const landmarks = uniqueById([...flatLandmarks, ...nestedLandmarks]);
  const selectedLandmarks = data?.selected_landmarks?.length
    ? data.selected_landmarks
    : landmarks.map((landmark) => landmark.selection_id).filter(Boolean);

  return {
    destinations: destinations.map(({ landmarks: _landmarks, ...destination }) => destination),
    landmarks,
    selectedLandmarks,
  };
};

export const splitQuickSuggestionLandmarks = (landmarks = []) => ({
  primary: landmarks.filter((landmark) => !landmark.is_alternative),
  alternatives: landmarks.filter((landmark) => landmark.is_alternative),
});

export const splitLandmarksBySource = (landmarks = []) => ({
  mentioned: landmarks.filter((landmark) => landmark.source_type === 'mentioned'),
  suggested: landmarks.filter((landmark) => landmark.source_type !== 'mentioned'),
});

export const defaultSelectedLandmarksForMode = (mapped = {}, mode = 'quick') => {
  if (mode === 'quick') {
    const mentionedIds = splitLandmarksBySource(mapped.landmarks).mentioned
      .map((landmark) => landmark.id)
      .filter(Boolean);
    if (mentionedIds.length > 0) {
      return mentionedIds;
    }
  }
  return mapped.selectedLandmarks || [];
};

const normalizedCoordinate = (value) => {
  const coordinate = Number(value);
  return Number.isFinite(coordinate) ? coordinate : null;
};

export const mappableLandmarks = (landmarks = []) =>
  landmarks
    .map((landmark) => {
      const latitude = normalizedCoordinate(landmark.latitude);
      const longitude = normalizedCoordinate(landmark.longitude);
      return latitude === null || longitude === null
        ? null
        : { ...landmark, latitude, longitude };
    })
    .filter(Boolean);

export const hasMappableCoordinates = (landmark = {}) => mappableLandmarks([landmark]).length === 1;

const landmarkLocationKey = (landmark = {}) =>
  [
    normalizeTextForMatching(landmark.name),
    normalizeTextForMatching(landmark.city),
    normalizeTextForMatching(landmark.country),
  ].join('|');

const uniqueNameIndex = (landmarks = []) => {
  const counts = landmarks.reduce((acc, landmark) => {
    const name = normalizeTextForMatching(landmark.name);
    if (name) {
      acc[name] = (acc[name] || 0) + 1;
    }
    return acc;
  }, {});
  return landmarks.reduce((acc, landmark) => {
    const name = normalizeTextForMatching(landmark.name);
    if (name && counts[name] === 1) {
      acc[name] = landmark;
    }
    return acc;
  }, {});
};

export const missingSelectedMapLandmarks = (landmarks = [], selectedLandmarks = []) => {
  const selectedSet = new Set(selectedLandmarks);
  return landmarks.filter(
    (landmark) => selectedSet.has(landmark.id) && !hasMappableCoordinates(landmark)
  );
};

export const mergeResolvedLandmarkLocations = (currentLandmarks = [], resolvedLandmarks = []) => {
  const resolvedById = resolvedLandmarks.reduce((acc, landmark) => {
    if (landmark?.id) {
      acc[landmark.id] = landmark;
    }
    return acc;
  }, {});
  const resolvedByLocationKey = resolvedLandmarks.reduce((acc, landmark) => {
    const key = landmarkLocationKey(landmark);
    if (key && key !== '||') {
      acc[key] = landmark;
    }
    return acc;
  }, {});
  const resolvedByName = uniqueNameIndex(resolvedLandmarks);

  return currentLandmarks.map((landmark) => {
    const resolved = resolvedById[landmark.id]
      || resolvedByLocationKey[landmarkLocationKey(landmark)]
      || resolvedByName[normalizeTextForMatching(landmark.name)];

    if (!resolved || !hasMappableCoordinates(resolved)) {
      return landmark;
    }

    const merged = {
      ...landmark,
      latitude: resolved.latitude,
      longitude: resolved.longitude,
      google_maps_uri: resolved.google_maps_uri || landmark.google_maps_uri || '',
      formatted_address: resolved.formatted_address || landmark.formatted_address || '',
      location_status: resolved.location_status || 'resolved',
    };

    if (!merged.image && resolved.image) {
      merged.image = resolved.image;
    }
    if ((!merged.image_attributions || merged.image_attributions.length === 0)
      && resolved.image_attributions?.length > 0) {
      merged.image_attributions = resolved.image_attributions;
    }

    return {
      ...merged,
      maps_url: resolved.maps_url || buildLandmarkMapsUrl(merged),
    };
  });
};

export const landmarkMapAction = (landmark = {}) => {
  const mapsUrl = landmark.maps_url || buildLandmarkMapsUrl(landmark);
  if (hasMappableCoordinates(landmark)) {
    return { mode: 'embedded', mapsUrl };
  }
  if (mapsUrl) {
    return { mode: 'external', mapsUrl };
  }
  return { mode: 'none', mapsUrl: '' };
};

export const tripMapExplorerItems = (landmarks = [], selectedLandmarks = []) => {
  const selectedSet = new Set(selectedLandmarks);
  return mappableLandmarks(landmarks)
    .map((landmark) => ({
      ...landmark,
      map_status: selectedSet.has(landmark.id) ? 'selected' : 'suggested',
    }))
    .sort((a, b) => {
      const selectedDelta = Number(b.map_status === 'selected') - Number(a.map_status === 'selected');
      if (selectedDelta !== 0) return selectedDelta;
      const alternativeDelta = Number(a.is_alternative) - Number(b.is_alternative);
      if (alternativeDelta !== 0) return alternativeDelta;
      return String(a.name || '').localeCompare(String(b.name || ''));
    });
};

export const tripMapVisibleItems = (
  landmarks = [],
  selectedLandmarks = [],
  includeSuggested = false,
) => {
  const items = tripMapExplorerItems(landmarks, selectedLandmarks);
  if (includeSuggested) {
    return items;
  }
  return items.filter((landmark) => landmark.map_status === 'selected');
};

export const mergeLandmarkSuggestions = (currentLandmarks = [], nextLandmarks = []) => {
  const seen = new Set(currentLandmarks.map((landmark) => landmark.id).filter(Boolean));
  const additions = nextLandmarks.filter((landmark) => {
    if (!landmark?.id || seen.has(landmark.id)) {
      return false;
    }
    seen.add(landmark.id);
    return true;
  });
  return [...currentLandmarks, ...additions];
};

export const mergeDestinationSuggestions = (currentDestinations = [], nextDestinations = []) => {
  const seen = new Set(currentDestinations.map((destination) => destination.id).filter(Boolean));
  const additions = nextDestinations.filter((destination) => {
    if (!destination?.id || seen.has(destination.id)) {
      return false;
    }
    seen.add(destination.id);
    return true;
  });
  return [...currentDestinations, ...additions];
};

export const selectGuideLandmarks = (landmarks = [], selectedLandmarks = []) => {
  if (!selectedLandmarks?.length) {
    return landmarks;
  }
  const byId = landmarks.reduce((acc, landmark) => {
    const selectionId = landmark.selection_id || landmark.id;
    if (selectionId) {
      acc[selectionId] = landmark;
    }
    if (landmark.id) {
      acc[landmark.id] = landmark;
    }
    return acc;
  }, {});
  return selectedLandmarks.map((selectionId) => byId[selectionId]).filter(Boolean);
};

export const appendGuideLandmarks = (formData, guideData) => {
  const landmarks = selectGuideLandmarks(guideData.landmarks || [], guideData.selectedLandmarks || []);
  const catalogLandmarkIds = landmarks
    .filter((landmark) => landmark.is_catalog_landmark)
    .map((landmark) => landmark.selection_id || landmark.id)
    .filter(Boolean);
  const customLandmarks = landmarks.filter((landmark) => !landmark.is_catalog_landmark);

  if (catalogLandmarkIds.length > 0) {
    catalogLandmarkIds.forEach((selectionId) => {
      formData.append('selected_landmarks', selectionId);
    });
  } else if (guideData.selectedLandmarks?.length > 0) {
    guideData.selectedLandmarks.forEach((selectionId) => {
      formData.append('selected_landmarks', selectionId);
    });
  }

  if (customLandmarks.length > 0) {
    const customLandmarksPayload = JSON.stringify(
      customLandmarks.map((landmark) => {
        const payload = {
          selection_id: landmark.selection_id || landmark.id,
          name: landmark.name,
          city: landmark.city,
          country: landmark.country,
          description: Array.isArray(landmark.description_paragraphs)
            ? landmark.description_paragraphs.slice(0, 3)
            : [landmark.description].filter(Boolean).slice(0, 3),
        };
        if (landmark.image) {
          payload.image = landmark.image;
        }
        if (landmark.image_attributions?.length > 0) {
          payload.image_attributions = landmark.image_attributions;
        }
        if (landmark.place_id) {
          // Chave do cache global de arte estilizada no backend.
          payload.place_id = landmark.place_id;
        }
        return payload;
      })
    );
    formData.append('custom_landmarks', customLandmarksPayload);
  }
};

export const appendGuideMetadata = (formData, guideData = {}) => {
  formData.append('title', guideData.title || 'Guia de Viagem');
  if (guideData.childrenNames) formData.append('children_names', guideData.childrenNames);
  if (Array.isArray(guideData.childrenAges)) {
    guideData.childrenAges
      .map((age) => Number.parseInt(age, 10))
      .filter((age) => Number.isFinite(age) && age > 0)
      .forEach((age) => formData.append('children_ages', String(age)));
  }
  if (guideData.parentsNames) formData.append('parents_names', guideData.parentsNames);
  if (guideData.year) formData.append('year', guideData.year.toString());
  const expectedFamilyMemberCount = Number.parseInt(
    guideData.expectedVisibleFamilyMemberCount,
    10,
  );
  if (Number.isFinite(expectedFamilyMemberCount) && expectedFamilyMemberCount > 0) {
    formData.append(
      'expected_visible_family_member_count',
      String(Math.min(expectedFamilyMemberCount, 20)),
    );
  }
  if (guideData.restaurantRecommendationsExtra) {
    formData.append('restaurant_recommendations_extra', 'true');
  }
  if (guideData.itinerary) {
    formData.append('itinerary_json', JSON.stringify(guideData.itinerary));
  }
  formData.append(
    'activity_selections_json',
    JSON.stringify(normalizeLandmarkActivitySelections(guideData.landmarkActivitySelections)),
  );
  if (guideData.photoProcessingConsent) {
    formData.append('photo_processing_consent', 'true');
  }
  if (guideData.privacyConsentVersion) {
    formData.append('privacy_consent_version', String(guideData.privacyConsentVersion));
  }
  if (guideData.privacyConsentAt) {
    formData.append('privacy_consent_at', String(guideData.privacyConsentAt));
  }
};

const guideItineraryStop = (landmark = {}) => {
  const selectionId = landmark.selection_id || landmark.id;
  const name = String(landmark.name || '').trim();
  if (!selectionId || !name) {
    return null;
  }
  return {
    selection_id: String(selectionId),
    name,
    destination_id: landmark.destination_id ? String(landmark.destination_id) : null,
  };
};

export const buildGuideItineraryPayload = ({
  itineraryMode = 'known',
  destinationsList = [],
  itineraryPreferences = {},
  recommendedDays = [],
  extraLandmarks = [],
} = {}) => {
  const destinations = normalizeGuideDestinations(destinationsList)
    .filter((item) => item.place && item.timing && item.days > 0)
    .map((item, index) => ({
      id: String(item.id || `destination-${index + 1}`),
      place: item.place,
      timing: item.timing,
      days: item.days,
      order: index + 1,
    }));

  if (destinations.length === 0) {
    return null;
  }

  const validModes = new Set(['known', 'freeform', 'suggested']);
  const validPaces = new Set(['light', 'balanced', 'full']);
  const days = recommendedDays
    .map((day, index) => ({
      day: Number.parseInt(day.day, 10) || index + 1,
      title: String(day.title || `Dia ${index + 1}`).trim(),
      theme: String(day.theme || '').trim(),
      stops: (day.landmarks || []).map(guideItineraryStop).filter(Boolean),
    }))
    .filter((day) => day.stops.length > 0);

  return {
    mode: validModes.has(itineraryMode) ? itineraryMode : 'known',
    pace: validPaces.has(itineraryPreferences.pace) ? itineraryPreferences.pace : 'balanced',
    interests: (itineraryPreferences.interests || [])
      .map((interest) => String(interest).trim())
      .filter(Boolean)
      .slice(0, 12),
    destinations,
    days,
    unplanned_stops: extraLandmarks.map(guideItineraryStop).filter(Boolean),
  };
};

const stripDestinationLandmarks = ({ landmarks: _landmarks, ...destination }) => destination;

export const buildDiscoverItineraryPayload = ({
  destination = '',
  destinationsList = [],
  itineraryPreferences = {},
  childrenList = [],
} = {}) => {
  const structuredDestinations = normalizeGuideDestinations(destinationsList)
    .filter((item) => item.place && item.timing && item.days > 0);
  const destinationSummary = structuredDestinations.length > 0
    ? serializeGuideDestinations(structuredDestinations)
    : String(destination || '').trim();
  const days = totalTripDays(structuredDestinations) || Number(itineraryPreferences.days) || 3;

  return {
    destination: destinationSummary,
    days,
    interests: itineraryPreferences.interests || [],
    pace: itineraryPreferences.pace || 'balanced',
    children_ages: deriveChildAges(childrenList),
    must_see: [],
    structured_destinations: structuredDestinations.map(stripDestinationLandmarks),
  };
};

export const buildRouteSuggestionPayload = ({
  tripIdea = '',
  destinationsList = [],
  itineraryPreferences = {},
  childrenList = [],
} = {}) => {
  const structuredDestinations = normalizeGuideDestinations(destinationsList)
    .filter((item) => item.place && item.timing && item.days > 0);
  const explicitDays = Number.parseInt(itineraryPreferences.days, 10);

  return {
    trip_idea: String(tripIdea || '').trim(),
    days: Number.isFinite(explicitDays) && explicitDays > 0
      ? explicitDays
      : totalTripDays(structuredDestinations) || 3,
    pace: itineraryPreferences.pace || 'balanced',
    interests: itineraryPreferences.interests || [],
    children_ages: deriveChildAges(childrenList),
    structured_destinations: structuredDestinations.map(stripDestinationLandmarks),
  };
};

const responseErrorMessage = async (response, fallbackMessage) => {
  const payload = await response.json().catch(() => ({}));
  const detail = payload?.detail;

  if (typeof detail === 'string' && detail.trim()) return detail;
  if (typeof detail?.message === 'string' && detail.message.trim()) return detail.message;
  if (typeof payload?.message === 'string' && payload.message.trim()) return payload.message;
  return `${fallbackMessage} (${response.status})`;
};

const guideDetailsUrl = (guideId) => {
  const normalizedGuideId = String(guideId || '').trim();
  if (!normalizedGuideId) throw new Error('Identificador do guia inválido.');
  return `${apiBaseUrl()}/api/guides/${encodeURIComponent(normalizedGuideId)}`;
};

export const listGuides = async ({ signal } = {}) => {
  const response = await authenticatedFetch(`${apiBaseUrl()}/api/guides`, {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível carregar seus guias'));
  }

  const payload = await response.json();
  return Array.isArray(payload?.guides) ? payload.guides : [];
};

const draftUrl = (draftId = '') => {
  const suffix = draftId ? `/${encodeURIComponent(String(draftId))}` : '';
  return `${apiBaseUrl()}/api/drafts${suffix}`;
};

export const getCurrentGuideDraft = async ({ signal } = {}) => {
  const response = await authenticatedFetch(`${draftUrl()}/current`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível recuperar o rascunho'));
  }
  const payload = await response.json();
  return payload?.draft || null;
};

export const createGuideDraft = async ({ title = '', payload = {} }, { signal } = {}) => {
  const response = await authenticatedFetch(draftUrl(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ title, payload }),
    signal,
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível salvar o rascunho'));
  }
  return response.json();
};

export const updateGuideDraft = async (
  draftId,
  { title = '', payload = {}, revision },
  { signal } = {},
) => {
  const response = await authenticatedFetch(draftUrl(draftId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ title, payload, revision }),
    signal,
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível salvar o rascunho'));
  }
  return response.json();
};

export const discardGuideDraft = async (draftId, { signal } = {}) => {
  const response = await authenticatedFetch(draftUrl(draftId), {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível descartar o rascunho'));
  }
  return (await response.json())?.deleted === true;
};

export const getGuide = async (guideId, { signal } = {}) => {
  const response = await authenticatedFetch(guideDetailsUrl(guideId), {
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível carregar o guia'));
  }

  return response.json();
};

export const deleteGuide = async (guideId, { signal } = {}) => {
  const response = await authenticatedFetch(guideDetailsUrl(guideId), {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível excluir o guia'));
  }

  const payload = await response.json();
  return payload?.deleted === true;
};

const safeDownloadUrl = (downloadUrl) => {
  const browserOrigin = globalThis.location?.origin || DEFAULT_API_BASE_URL;
  const baseUrl = new URL(
    `${apiBaseUrl().replace(/\/$/, '')}/`,
    `${browserOrigin.replace(/\/$/, '')}/`,
  );
  const resolvedUrl = new URL(String(downloadUrl || ''), baseUrl);
  const validPath = resolvedUrl.pathname.startsWith('/download/')
    || /^\/guide-builder\/[A-Za-z0-9]+\/pdf$/.test(resolvedUrl.pathname);
  if (resolvedUrl.origin !== baseUrl.origin || !validPath) {
    throw new Error('Link de download inválido.');
  }
  return resolvedUrl.toString();
};

const downloadFilename = (response, downloadUrl) => {
  const disposition = response.headers.get('Content-Disposition') || '';
  const encodedFilename = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plainFilename = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  const fallbackFilename = decodeURIComponent(new URL(downloadUrl).pathname.split('/').at(-1) || 'guia.pdf');
  const filename = encodedFilename ? decodeURIComponent(encodedFilename) : plainFilename;
  return String(filename || fallbackFilename).replace(/[\\/]/g, '-');
};

export const downloadGuidePdf = async (downloadUrl, { signal } = {}) => {
  const resolvedUrl = safeDownloadUrl(downloadUrl);
  const response = await authenticatedFetch(resolvedUrl, {
    headers: { Accept: 'application/pdf' },
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível baixar o guia'));
  }

  return {
    blob: await response.blob(),
    filename: downloadFilename(response, resolvedUrl),
  };
};

const safeGuidePreviewUrl = (previewUrl) => {
  const browserOrigin = globalThis.location?.origin || DEFAULT_API_BASE_URL;
  const baseUrl = new URL(
    `${apiBaseUrl().replace(/\/$/, '')}/`,
    `${browserOrigin.replace(/\/$/, '')}/`,
  );
  const resolvedUrl = new URL(String(previewUrl || ''), baseUrl);
  const validPath = /^\/guides\/[A-Za-z0-9-]+\/preview$/.test(resolvedUrl.pathname);
  if (resolvedUrl.origin !== baseUrl.origin || !validPath) {
    throw new Error('Link de prévia inválido.');
  }
  return resolvedUrl.toString();
};

export const fetchGuidePreviewHtml = async (previewUrl, { signal } = {}) => {
  const resolvedUrl = safeGuidePreviewUrl(previewUrl);
  const response = await authenticatedFetch(resolvedUrl, {
    headers: { Accept: 'text/html' },
    signal,
  });

  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível carregar a prévia'));
  }

  return response.text();
};

export const fetchCatalog = async () => {
  const baseUrl = apiBaseUrl();

  const response = await authenticatedFetch(`${baseUrl}/api/catalog`, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Erro do servidor: ${response.status}`);
  }

  return response.json();
};

export const recommendItinerary = async (payload) => {
  const baseUrl = apiBaseUrl();

  const response = await authenticatedFetch(`${baseUrl}/api/itinerary/recommend`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Erro do servidor: ${response.status}`);
  }

  return response.json();
};

export const discoverItinerary = async (payload) => {
  const baseUrl = apiBaseUrl();

  const response = await authenticatedFetch(`${baseUrl}/api/itinerary/discover`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Erro do servidor: ${response.status}`);
  }

  return response.json();
};

export const suggestItineraryRoutes = async (payload) => {
  const baseUrl = apiBaseUrl();

  const response = await authenticatedFetch(`${baseUrl}/api/itinerary/routes/suggest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Erro do servidor: ${response.status}`);
  }

  return response.json();
};

export const buildStructuredLandmarksPayload = ({ destinationsList = [] } = {}) => ({
  destinations: normalizeGuideDestinations(destinationsList)
    .filter((item) => item.place && item.landmarks.length > 0)
    .map((item) => ({ place: item.place, landmarks: item.landmarks })),
});

export const resolveStructuredLandmarks = async (payload) => {
  const baseUrl = apiBaseUrl();

  try {
    const response = await authenticatedFetch(`${baseUrl}/api/landmarks/resolve-structured`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Erro do servidor: ${response.status}`);
    }

    const data = await response.json();

    return {
      destinations: data.destinations || [],
      landmarks: data.landmarks || [],
      selected_landmarks: data.selected_landmarks || [],
    };
  } catch (error) {
    console.error('Minerva API Error:', error);
    throw new Error(
      error.message.includes('Failed to fetch')
        ? 'Erro de rede: Verifique sua conexão com a internet.'
        : error.message || 'Não foi possível organizar os pontos turísticos informados.'
    );
  }
};

export const parseLandmarks = async (message) => {
  const baseUrl = apiBaseUrl();

  try {
    const response = await authenticatedFetch(`${baseUrl}/api/landmarks/parse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `Erro do servidor: ${response.status}`);
    }

    const data = await response.json();

    // Ensure the response matches the expected shape, providing fallbacks if necessary
    return {
      destinations: data.destinations || [],
      landmarks: data.landmarks || [],
      selected_landmarks: data.selected_landmarks || []
    };
  } catch (error) {
    console.error('Minerva API Error:', error);
    throw new Error(
      error.message.includes('Failed to fetch')
        ? 'Erro de rede: Verifique sua conexão com a internet.'
        : 'Não foi possível processar seu roteiro no momento. Tente novamente.'
    );
  }
};

export const generatePDF = async (guideData, { idempotencyKey } = {}) => {
  const baseUrl = apiBaseUrl();

  try {
    const formData = new FormData();

    // Append basic fields
    appendGuideMetadata(formData, guideData);

    // Append file if exists
    if (guideData.familyPhoto) {
      formData.append('family_photo', guideData.familyPhoto);
    }

    appendGuideLandmarks(formData, guideData);

    const response = await authenticatedFetch(`${baseUrl}/api/generate`, {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey || createIdempotencyKey(),
      },
      // Do NOT set Content-Type header, let the browser set it with the correct boundary for FormData
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Erro do servidor: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Minerva API PDF Generation Error:', error);
    throw new Error('Não foi possível gerar o PDF.');
  }
};

const builderRequest = async (path, { method = 'POST', body } = {}) => {
  const response = await authenticatedFetch(`${apiBaseUrl()}${path}`, {
    method,
    ...(body
      ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      : {}),
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível montar o guia'));
  }
  return response.json();
};

export const createGuideBuilder = async (guideData) => {
  const formData = new FormData();
  appendGuideMetadata(formData, guideData);
  if (guideData.familyPhoto) {
    formData.append('family_photo', guideData.familyPhoto);
  }
  appendGuideLandmarks(formData, guideData);

  const response = await authenticatedFetch(`${apiBaseUrl()}/api/guide-builder`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível iniciar a montagem'));
  }
  return response.json();
};

export const fetchGuideBuilderSession = async (sessionId) =>
  builderRequest(`/api/guide-builder/${encodeURIComponent(sessionId)}`, {
    method: 'GET',
  });

export const generateBuilderPageAttempt = async (
  sessionId,
  pageId,
  idempotencyKey,
  revisionInstruction = '',
  includeFamily = false,
) => {
  const response = await authenticatedFetch(
    `${apiBaseUrl()}/api/guide-builder/${encodeURIComponent(sessionId)}/pages/${encodeURIComponent(pageId)}/attempts`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey || createIdempotencyKey(),
      },
      body: JSON.stringify({
        revision_instruction: revisionInstruction.trim(),
        include_family: includeFamily,
      }),
    },
  );
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível gerar esta página'));
  }
  return response.json();
};

export const selectBuilderPageAttempt = async (sessionId, pageId, attemptId) =>
  builderRequest(
    `/api/guide-builder/${encodeURIComponent(sessionId)}/pages/${encodeURIComponent(pageId)}/selection`,
    {
      method: 'PATCH',
      body: { attempt_id: attemptId },
    },
  );

export const approveBuilderPage = async (sessionId, pageId, attemptId) =>
  builderRequest(
    `/api/guide-builder/${encodeURIComponent(sessionId)}/pages/${encodeURIComponent(pageId)}/approve`,
    {
      body: { attempt_id: attemptId },
    },
  );

export const completeGuideBuilder = async (sessionId) =>
  builderRequest(`/api/guide-builder/${encodeURIComponent(sessionId)}/complete`, {
    method: 'POST',
  });

export const generateBuilderPdf = async (sessionId) =>
  builderRequest(`/api/guide-builder/${encodeURIComponent(sessionId)}/pdf`, {
    method: 'POST',
  });

const safeBuilderAssetUrl = (assetUrl) => {
  const browserOrigin = globalThis.location?.origin || DEFAULT_API_BASE_URL;
  const baseUrl = new URL(
    `${apiBaseUrl().replace(/\/$/, '')}/`,
    `${browserOrigin.replace(/\/$/, '')}/`,
  );
  const resolvedUrl = new URL(String(assetUrl || ''), baseUrl);
  const validPath = /^\/guide-builder\/[A-Za-z0-9]+\/assets\/[\w.-]+$/.test(resolvedUrl.pathname);
  if (resolvedUrl.origin !== baseUrl.origin || !validPath) {
    throw new Error('Link de imagem inválido.');
  }
  return resolvedUrl.toString();
};

export const fetchBuilderAssetObjectUrl = async (assetUrl) => {
  const response = await authenticatedFetch(safeBuilderAssetUrl(assetUrl), {
    headers: { Accept: 'image/png' },
  });
  if (!response.ok) {
    throw new Error(await responseErrorMessage(response, 'Não foi possível carregar a imagem'));
  }
  return URL.createObjectURL(await response.blob());
};

export const getGuideJob = async (jobId, { signal } = {}) => {
  const safeJobId = String(jobId || '').trim();
  if (!safeJobId) {
    throw new Error('Identificador da geração inválido.');
  }
  const response = await authenticatedFetch(`${apiBaseUrl()}/api/jobs/${encodeURIComponent(safeJobId)}`, {
    method: 'GET',
    signal,
  });
  if (!response.ok) {
    throw new Error(`Não foi possível consultar a geração (${response.status}).`);
  }
  return response.json();
};

export const waitForGuideJob = async (
  jobId,
  {
    onUpdate = () => {},
    intervalMs = 1000,
    maxAttempts = 180,
    signal,
    sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
  } = {},
) => {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const job = await getGuideJob(jobId, { signal });
    onUpdate(job);
    if (job.status === 'succeeded' && job.result?.download_url) {
      return job.result;
    }
    if (job.status === 'failed') {
      throw new Error(job.error?.message || 'Não foi possível gerar o guia.');
    }
    if (job.status === 'cancelled') {
      throw new Error('A geração foi cancelada.');
    }
    if (attempt < maxAttempts - 1) {
      await sleep(intervalMs);
    }
  }
  throw new Error('A geração está demorando mais que o esperado. Acompanhe-a no seu painel.');
};
