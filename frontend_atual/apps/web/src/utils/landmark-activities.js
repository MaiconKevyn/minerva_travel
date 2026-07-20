export const OPTIONAL_LANDMARK_ACTIVITY_TYPES = [
  'detail_hunt',
  'word_search',
  'drawing',
  'coloring',
];

export const MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK = 2;
export const MAX_OPTIONAL_ACTIVITIES_PER_GUIDE = 8;

export const LANDMARK_ACTIVITY_OPTIONS = [
  {
    type: 'detail_hunt',
    label: 'Caça aos detalhes',
    description: 'Observe a ilustração e marque detalhes especiais do lugar.',
    ageLabel: 'A partir de 5 anos',
    durationLabel: '5–10 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/detail-hunt.svg',
  },
  {
    type: 'word_search',
    label: 'Caça-palavras',
    description: 'Encontre palavras ligadas ao ponto turístico e à cidade.',
    ageLabel: 'A partir de 6 anos',
    durationLabel: '10–15 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/word-search.svg',
  },
  {
    type: 'drawing',
    label: 'Desenhe sua versão',
    description: 'Complete uma moldura inspirada no lugar com seu próprio desenho.',
    ageLabel: 'A partir de 4 anos',
    durationLabel: '10–20 min',
    materialLabel: 'Lápis ou canetinha',
    preview: '/activity-examples/drawing.svg',
  },
  {
    type: 'coloring',
    label: 'Página para colorir',
    description:
      'Um desenho do ponto turístico com traços limpos, formas grandes e uma frase personalizada para colorir.',
    ageLabel: 'A partir de 4 anos',
    durationLabel: '15–25 min',
    materialLabel: 'Lápis de cor',
    preview: '/activity-examples/coloring.svg',
  },
];

const allowedTypes = new Set(OPTIONAL_LANDMARK_ACTIVITY_TYPES);

const selectionId = (value) => String(value || '').trim();

export const normalizeLandmarkActivitySelections = (selections = []) => {
  if (!Array.isArray(selections)) return [];

  const seen = new Set();
  const perLandmark = new Map();
  const normalized = [];

  selections.forEach((selection) => {
    const landmarkSelectionId = selectionId(selection?.landmark_selection_id);
    const activityType = selectionId(selection?.activity_type);
    if (!landmarkSelectionId || !allowedTypes.has(activityType)) return;

    const key = `${landmarkSelectionId}:${activityType}`;
    const landmarkCount = perLandmark.get(landmarkSelectionId) || 0;
    if (
      seen.has(key) ||
      landmarkCount >= MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK ||
      normalized.length >= MAX_OPTIONAL_ACTIVITIES_PER_GUIDE
    ) {
      return;
    }

    seen.add(key);
    perLandmark.set(landmarkSelectionId, landmarkCount + 1);
    normalized.push({
      landmark_selection_id: landmarkSelectionId,
      activity_type: activityType,
      order: landmarkCount + 1,
    });
  });

  return normalized;
};

export const pruneLandmarkActivitySelections = (selections = [], selectedLandmarks = []) => {
  const selected = new Set((selectedLandmarks || []).map(selectionId).filter(Boolean));
  return normalizeLandmarkActivitySelections(selections).filter(
    (selection) => selected.has(selection.landmark_selection_id),
  );
};

export const toggleLandmarkActivitySelection = (
  selections,
  landmarkSelectionId,
  activityType,
) => {
  const normalized = normalizeLandmarkActivitySelections(selections);
  const landmarkId = selectionId(landmarkSelectionId);
  const type = selectionId(activityType);
  if (!landmarkId || !allowedTypes.has(type)) {
    return { selections: normalized, error: 'Atividade inválida.' };
  }

  const exists = normalized.some(
    (selection) =>
      selection.landmark_selection_id === landmarkId && selection.activity_type === type,
  );
  if (exists) {
    return {
      selections: normalizeLandmarkActivitySelections(
        normalized.filter(
          (selection) =>
            !(
              selection.landmark_selection_id === landmarkId &&
              selection.activity_type === type
            ),
        ),
      ),
      error: '',
    };
  }

  const pointCount = normalized.filter(
    (selection) => selection.landmark_selection_id === landmarkId,
  ).length;
  if (pointCount >= MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK) {
    return {
      selections: normalized,
      error: `Escolha no máximo ${MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK} atividades por ponto turístico.`,
    };
  }
  if (normalized.length >= MAX_OPTIONAL_ACTIVITIES_PER_GUIDE) {
    return {
      selections: normalized,
      error: `Escolha no máximo ${MAX_OPTIONAL_ACTIVITIES_PER_GUIDE} atividades opcionais por guia.`,
    };
  }

  return {
    selections: normalizeLandmarkActivitySelections([
      ...normalized,
      {
        landmark_selection_id: landmarkId,
        activity_type: type,
        order: pointCount + 1,
      },
    ]),
    error: '',
  };
};

export const activityOptionForType = (activityType) =>
  LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === activityType) || null;
