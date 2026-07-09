export const createGuideDestination = (index = 0) => ({
  id: `destination-${index + 1}`,
  place: '',
  timing: '',
  days: 1,
  landmarks: [''],
});

const normalizePositiveInteger = (value) => {
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) && number > 0 ? number : 0;
};

export const normalizeDestinationLandmarks = (landmarks = []) =>
  landmarks
    .map((landmark) => String(landmark || '').trim())
    .filter(Boolean);

export const normalizeFamilyMemberCount = (value) => {
  const count = normalizePositiveInteger(value);
  return count > 0 ? Math.min(count, 20) : 0;
};

export const normalizeGuideDestinations = (destinations = []) =>
  destinations.map((destination, index) => ({
    id: destination.id || `destination-${index + 1}`,
    place: String(destination.place || '').trim(),
    timing: String(destination.timing || '').trim(),
    days: normalizePositiveInteger(destination.days),
    landmarks: normalizeDestinationLandmarks(destination.landmarks),
  }));

export const normalizeRouteSuggestionDestinations = (destinations = []) =>
  destinations.map((destination, index) => ({
    id: `suggested-${index + 1}`,
    place: String(destination.place || '').trim(),
    timing: String(destination.timing || '').trim(),
    days: normalizePositiveInteger(destination.days),
  }));

export const validGuideDestinations = (destinations = []) => {
  const normalized = normalizeGuideDestinations(destinations);
  return (
    normalized.length > 0 &&
    normalized.every((destination) => (
      Boolean(destination.place) &&
      Boolean(destination.timing) &&
      destination.days > 0
    ))
  );
};

export const validKnownGuideDestinations = (destinations = []) => {
  const normalized = normalizeGuideDestinations(destinations);
  return (
    validGuideDestinations(normalized) &&
    normalized.every((destination) => destination.landmarks.length > 0)
  );
};

export const totalTripDays = (destinations = []) =>
  normalizeGuideDestinations(destinations).reduce(
    (total, destination) => total + Math.max(destination.days, 0),
    0,
  );

export const serializeGuideDestinations = (destinations = []) =>
  normalizeGuideDestinations(destinations)
    .filter((destination) => destination.place || destination.timing || destination.days > 0)
    .map((destination, index) => {
      const dayLabel = destination.days === 1 ? '1 dia' : `${destination.days} dias`;
      const landmarkSuffix = destination.landmarks.length > 0
        ? ` pontos turísticos: ${destination.landmarks.join(', ')}.`
        : '';
      return `Destino ${index + 1}: ${destination.place}; quando: ${destination.timing}; duração: ${dayLabel}.${landmarkSuffix}`;
    })
    .join('\n');

export const normalizeGuideChildren = (children = []) =>
  children.map((child, index) => ({
    id: child.id || `child-${index + 1}`,
    name: String(child.name || '').trim(),
    age: normalizePositiveInteger(child.age),
  }));

export const validGuideChildren = (children = []) =>
  normalizeGuideChildren(children).filter((child) => child.name && child.age > 0);

export const guideChildrenAreComplete = (children = []) => {
  const normalized = normalizeGuideChildren(children);
  return normalized.length > 0 && normalized.every((child) => child.name && child.age > 0);
};

export const deriveChildNames = (children = []) =>
  validGuideChildren(children).map((child) => child.name);

export const deriveChildAges = (children = []) =>
  validGuideChildren(children).map((child) => child.age);

export const guideChildRecordsForSubmit = (children = []) =>
  validGuideChildren(children).map(({ name, age }) => ({ name, age }));

export const deriveExpectedFamilyMemberCount = ({
  childrenList = [],
  parentsList = [],
} = {}) => {
  const childCount = validGuideChildren(childrenList).length;
  const parentCount = parentsList.filter((name) => String(name || '').trim()).length;
  return normalizeFamilyMemberCount(childCount + parentCount);
};

const ORDER_MARKER_PATTERN = /\b(primeiro|primeira|depois|em seguida|ent[aã]o|por fim|1[ºo]?|2[ºo]?|3[ºo]?)\b|[;\n]/i;
const TIMING_PATTERN = /\bem\s+(.+?)(?:\s+por\s+\d+\s+dias?|\s*$)/i;
const DAYS_PATTERN = /\b(?:por|durante)\s+(\d+)\s+dias?\b/i;

export const parseFreeformItineraryText = (text = '') => {
  const rawText = String(text || '').trim();
  if (!rawText) {
    return { destinations: [], followUpQuestions: [] };
  }

  const ambiguousOrder = !ORDER_MARKER_PATTERN.test(rawText) && /\s+e\s+/i.test(rawText);
  const segments = ambiguousOrder
    ? splitAmbiguousDestinationList(rawText)
    : rawText
      .split(/(?:[;\n]+|\s+\bdepois\b\s+|\s+\bem seguida\b\s+|\s+\bpor fim\b\s+)/i)
      .map((segment) => segment.trim())
      .filter(Boolean);

  const destinations = segments.map((segment, index) => parseFreeformSegment(segment, index));
  const followUpQuestions = [];

  if (ambiguousOrder && destinations.length > 1) {
    followUpQuestions.push({
      field: 'order',
      destinationId: null,
      message: 'Qual é a ordem correta dos destinos?',
    });
  }

  destinations.forEach((destination) => {
    if (destination.place && destination.days <= 0) {
      followUpQuestions.push({
        field: 'days',
        destinationId: destination.id,
        message: `Por quantos dias a família ficará em ${destination.place}?`,
      });
    }
    if (destination.place && !destination.timing) {
      followUpQuestions.push({
        field: 'timing',
        destinationId: destination.id,
        message: `Quando a família vai para ${destination.place}?`,
      });
    }
  });

  return { destinations, followUpQuestions };
};

const splitAmbiguousDestinationList = (text) => {
  const beforeTiming = text.split(/\bem\b/i)[0] || text;
  return beforeTiming
    .replace(DAYS_PATTERN, '')
    .split(/\s+e\s+/i)
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((place) => {
      const timing = text.match(TIMING_PATTERN)?.[1]?.trim().replace(/[.。]$/, '') || '';
      const days = text.match(DAYS_PATTERN)?.[1] || '';
      return `${place}${timing ? ` em ${timing}` : ''}${days ? ` por ${days} dias` : ''}`;
    });
};

const parseFreeformSegment = (segment, index) => {
  const cleaned = segment
    .replace(/^(primeiro|primeira|ent[aã]o|depois|em seguida|por fim|1[ºo]?|2[ºo]?|3[ºo]?)\s+/i, '')
    .trim()
    .replace(/[.。]$/, '');
  const days = normalizePositiveInteger(cleaned.match(DAYS_PATTERN)?.[1] || '');
  const timing = (cleaned.match(TIMING_PATTERN)?.[1] || '')
    .trim()
    .replace(/[.。]$/, '');
  const place = cleaned
    .replace(TIMING_PATTERN, '')
    .replace(DAYS_PATTERN, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/[,.]$/, '');

  return {
    id: `freeform-${index + 1}`,
    place,
    timing,
    days,
  };
};
