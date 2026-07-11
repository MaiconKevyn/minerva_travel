export const MAX_GUIDE_CHILDREN = 10;
export const MAX_GUIDE_PARENTS = 10;
export const MAX_GUIDE_DESTINATIONS = 10;
export const MAX_GUIDE_LANDMARKS = 30;
export const MAX_VISIBLE_FAMILY_MEMBERS = 20;
export const MIN_GUIDE_YEAR = 2024;
export const MAX_GUIDE_YEAR = 2100;
export const FAMILY_PHOTO_MAX_BYTES = 10 * 1024 * 1024;
export const FAMILY_PHOTO_MAX_PIXELS = 40_000_000;
export const FAMILY_PHOTO_MAX_WIDTH = 12_000;
export const FAMILY_PHOTO_MAX_HEIGHT = 12_000;
export const PRIVACY_CONSENT_VERSION = '2026-07-09';

const FAMILY_PHOTO_FORMATS = {
  'image/jpeg': { extensions: ['.jpg', '.jpeg'], format: 'jpeg' },
  'image/png': { extensions: ['.png'], format: 'png' },
  'image/webp': { extensions: ['.webp'], format: 'webp' },
};

const fileExtension = (name = '') => {
  const normalized = String(name).trim().toLowerCase();
  const dotIndex = normalized.lastIndexOf('.');
  return dotIndex >= 0 ? normalized.slice(dotIndex) : '';
};

const detectedFamilyPhotoFormat = (bytes) => {
  if (
    bytes.length >= 3 &&
    bytes[0] === 0xff &&
    bytes[1] === 0xd8 &&
    bytes[2] === 0xff
  ) return 'jpeg';
  if (
    bytes.length >= 8 &&
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47 &&
    bytes[4] === 0x0d &&
    bytes[5] === 0x0a &&
    bytes[6] === 0x1a &&
    bytes[7] === 0x0a
  ) return 'png';
  if (
    bytes.length >= 12 &&
    String.fromCharCode(...bytes.slice(0, 4)) === 'RIFF' &&
    String.fromCharCode(...bytes.slice(8, 12)) === 'WEBP'
  ) return 'webp';
  return null;
};

const decodeBrowserImageDimensions = async (file) => {
  if (typeof globalThis.createImageBitmap === 'function') {
    const bitmap = await globalThis.createImageBitmap(file);
    const dimensions = { width: bitmap.width, height: bitmap.height };
    bitmap.close?.();
    return dimensions;
  }
  if (typeof globalThis.Image !== 'function' || !globalThis.URL?.createObjectURL) {
    throw new Error('Não foi possível ler as dimensões da imagem neste navegador.');
  }
  const objectUrl = globalThis.URL.createObjectURL(file);
  try {
    return await new Promise((resolve, reject) => {
      const image = new globalThis.Image();
      image.onload = () => resolve({ width: image.naturalWidth, height: image.naturalHeight });
      image.onerror = () => reject(new Error('A imagem está corrompida ou incompleta.'));
      image.src = objectUrl;
    });
  } finally {
    globalThis.URL.revokeObjectURL(objectUrl);
  }
};

export const validateFamilyPhoto = async (
  file,
  { decodeDimensions = decodeBrowserImageDimensions } = {},
) => {
  if (!file || typeof file.slice !== 'function') {
    return { valid: false, code: 'missing_file', message: 'Escolha uma foto para continuar.' };
  }
  if (!file.size) {
    return { valid: false, code: 'empty_file', message: 'A foto selecionada está vazia.' };
  }
  if (file.size > FAMILY_PHOTO_MAX_BYTES) {
    return {
      valid: false,
      code: 'file_too_large',
      message: 'A foto deve ter no máximo 10 MB.',
    };
  }
  const mimeType = String(file.type || '').toLowerCase();
  const format = FAMILY_PHOTO_FORMATS[mimeType];
  const extension = fileExtension(file.name);
  if (!format || !format.extensions.includes(extension)) {
    return {
      valid: false,
      code: 'unsupported_type',
      message: 'Envie uma foto JPEG, PNG ou WebP com a extensão correta.',
    };
  }
  try {
    const header = new Uint8Array(await file.slice(0, 12).arrayBuffer());
    if (detectedFamilyPhotoFormat(header) !== format.format) {
      return {
        valid: false,
        code: 'content_mismatch',
        message: 'O conteúdo da foto não corresponde ao tipo de arquivo informado.',
      };
    }
    const { width, height } = await decodeDimensions(file);
    if (
      !Number.isFinite(width) ||
      !Number.isFinite(height) ||
      width <= 0 ||
      height <= 0 ||
      width > FAMILY_PHOTO_MAX_WIDTH ||
      height > FAMILY_PHOTO_MAX_HEIGHT ||
      width * height > FAMILY_PHOTO_MAX_PIXELS
    ) {
      return {
        valid: false,
        code: 'dimensions_exceeded',
        message: 'A foto excede o limite de 12.000 px por lado ou 40 megapixels.',
      };
    }
  } catch (error) {
    return {
      valid: false,
      code: 'invalid_image',
      message: error?.message || 'A foto está corrompida ou não pôde ser lida.',
    };
  }
  return { valid: true, code: 'valid_image', message: '' };
};

let fallbackIdSequence = 0;

export const createGuideItemId = (prefix = 'guide-item') => {
  const randomUuid = globalThis.crypto?.randomUUID?.();
  if (randomUuid) return `${prefix}-${randomUuid}`;

  fallbackIdSequence += 1;
  return `${prefix}-${Date.now().toString(36)}-${fallbackIdSequence.toString(36)}`;
};

export const createGuideDestination = () => ({
  id: createGuideItemId('destination'),
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
