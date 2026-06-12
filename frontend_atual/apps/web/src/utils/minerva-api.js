
const DEFAULT_API_BASE_URL = 'https://minerva-travel.onrender.com';

export const apiBaseUrl = () => import.meta.env?.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;

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

const normalizeSourceType = (value) => (value === 'mentioned' ? 'mentioned' : 'suggested');

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
  source_type: normalizeSourceType(stop.source_type),
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
    source_type: normalizeSourceType(landmark.source_type || 'mentioned'),
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

export const appendGuideLandmarks = (formData, guideData) => {
  const landmarks = guideData.landmarks || [];
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
        return payload;
      })
    );
    formData.append('custom_landmarks', customLandmarksPayload);
  }
};

export const fetchCatalog = async () => {
  const baseUrl = apiBaseUrl();

  const response = await fetch(`${baseUrl}/api/catalog`, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Erro do servidor: ${response.status}`);
  }

  return response.json();
};

export const recommendItinerary = async (payload) => {
  const baseUrl = apiBaseUrl();

  const response = await fetch(`${baseUrl}/api/itinerary/recommend`, {
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

  const response = await fetch(`${baseUrl}/api/itinerary/discover`, {
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

export const parseLandmarks = async (message) => {
  const baseUrl = apiBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/api/landmarks/parse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
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

export const generatePDF = async (guideData) => {
  const baseUrl = apiBaseUrl();

  try {
    const formData = new FormData();

    // Append basic fields
    formData.append('title', guideData.title || 'Guia de Viagem');
    if (guideData.childrenNames) formData.append('children_names', guideData.childrenNames);
    if (guideData.parentsNames) formData.append('parents_names', guideData.parentsNames);
    if (guideData.year) formData.append('year', guideData.year.toString());

    // Append file if exists
    if (guideData.familyPhoto) {
      formData.append('family_photo', guideData.familyPhoto);
    }

    appendGuideLandmarks(formData, guideData);

    const response = await fetch(`${baseUrl}/api/generate`, {
      method: 'POST',
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
