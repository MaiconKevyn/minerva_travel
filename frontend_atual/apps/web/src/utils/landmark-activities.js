export const OPTIONAL_LANDMARK_ACTIVITY_TYPES = [
  'detail_hunt',
  'word_search',
  'drawing',
  'coloring',
  'family_coloring',
  'investigator',
  'newspaper_headline',
  'travel_diary',
  'here_vs_home',
  'anagram',
  'cryptogram',
  'maze',
  'crossword',
  'dot_to_dot',
  'postcard',
  'passport_stamp',
  'language_survival',
  'spot_the_difference',
];

export const MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK = 2;
export const MAX_OPTIONAL_ACTIVITIES_PER_GUIDE = 8;

/**
 * Onde a atividade acontece. Com poucas opções a lista corrida bastava; com o
 * catálogo cheio, o pai precisa saber num relance o que dá para fazer em pé na
 * fila e o que precisa de mesa e lápis de cor.
 */
export const ACTIVITY_CATEGORIES = [
  {
    id: 'onsite',
    label: 'No lugar',
    hint: 'Para fazer em pé, durante a visita.',
  },
  {
    id: 'puzzle',
    label: 'Quebra-cabeças',
    hint: 'Para a espera, o avião ou a noite no hotel.',
  },
  {
    id: 'art',
    label: 'Arte',
    hint: 'Precisa de mesa e lápis de cor.',
  },
  {
    id: 'writing',
    label: 'Escrever e lembrar',
    hint: 'Para quem já escreve sozinho.',
  },
];

export const LANDMARK_ACTIVITY_OPTIONS = [
  {
    type: 'detail_hunt',
    category: 'onsite',
    label: 'Caça aos detalhes',
    description: 'Observe a ilustração e marque detalhes especiais do lugar.',
    ageLabel: '5+',
    durationLabel: '5–10 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/detail-hunt-real.webp',
  },
  {
    type: 'investigator',
    category: 'onsite',
    label: 'Investigador',
    description:
      'Cada criança recebe uma pista e uma missão diferente, adaptada à idade e ao ponto turístico.',
    ageLabel: 'Todas',
    durationLabel: '10–20 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/investigator-real.webp',
  },
  {
    type: 'word_search',
    category: 'puzzle',
    label: 'Caça-palavras',
    description: 'Encontre palavras ligadas ao ponto turístico e à cidade.',
    ageLabel: '6+',
    durationLabel: '10–15 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/word-search-real.webp',
  },
  {
    type: 'maze',
    category: 'puzzle',
    label: 'Labirinto',
    description: 'Leva a família pelo labirinto até o ponto turístico. A grade cresce com a idade.',
    ageLabel: '4+',
    durationLabel: '5–10 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/maze-real.webp',
  },
  {
    type: 'dot_to_dot',
    category: 'puzzle',
    label: 'Ligue os pontos',
    description: 'Liga os números e a silhueta do ponto turístico aparece. Menos pontos para os menores.',
    ageLabel: '4+',
    durationLabel: '5–10 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/dot-to-dot-real.webp',
  },
  {
    type: 'anagram',
    category: 'puzzle',
    label: 'Palavras embaralhadas',
    description: 'Desembaralha os nomes do lugar, da cidade e do país, com a primeira letra de dica.',
    ageLabel: '7+',
    durationLabel: '5–10 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/anagram-real.webp',
  },
  {
    type: 'crossword',
    category: 'puzzle',
    label: 'Cruzadinha da viagem',
    description: 'Palavras cruzadas com dicas sobre a cidade, o país e o ponto turístico.',
    ageLabel: '9+',
    durationLabel: '15–20 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/crossword-real.webp',
  },
  {
    type: 'cryptogram',
    category: 'puzzle',
    label: 'Código secreto',
    description: 'Decifra com a chave numérica uma frase verdadeira sobre o ponto turístico.',
    ageLabel: '9+',
    durationLabel: '15–20 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/cryptogram-real.webp',
  },
  {
    type: 'spot_the_difference',
    category: 'puzzle',
    label: 'Ache os erros',
    description: 'Dois desenhos do lugar com seis diferenças conferidas uma a uma antes de imprimir.',
    ageLabel: '6+',
    durationLabel: '10–15 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/spot-the-difference-real.webp',
  },
  {
    type: 'coloring',
    category: 'art',
    label: 'Página para colorir',
    description:
      'Um desenho do ponto turístico com traços limpos, formas grandes e uma frase personalizada para colorir.',
    ageLabel: '4+',
    durationLabel: '15–25 min',
    materialLabel: 'Lápis de cor',
    preview: '/activity-examples/coloring-real.webp',
  },
  {
    type: 'family_coloring',
    category: 'art',
    label: 'Família de férias para colorir',
    description:
      'Usa a foto enviada como referência para transformar a família em um desenho fofo de férias no ponto turístico.',
    ageLabel: '4+',
    durationLabel: '15–25 min',
    materialLabel: 'Lápis de cor',
    preview: '/activity-examples/family-coloring-real.webp',
  },
  {
    type: 'drawing',
    category: 'art',
    label: 'Minha pintura',
    description: 'Use o espaço em branco para criar uma pintura do lugar do seu jeito.',
    ageLabel: '4+',
    durationLabel: '10–20 min',
    materialLabel: 'Tinta ou lápis',
    preview: '/activity-examples/painting-real.webp',
  },
  {
    type: 'language_survival',
    category: 'writing',
    label: 'Sobrevivência no idioma',
    description: 'Cinco frases do país para a criança pedir sozinha, com a pronúncia escrita.',
    ageLabel: '6+',
    durationLabel: '5–10 min',
    materialLabel: 'Só a boca',
    preview: '/activity-examples/language-survival-real.webp',
  },
  {
    type: 'postcard',
    category: 'writing',
    label: 'Cartão-postal',
    description: 'Frente com a arte do lugar e verso para escrever, recortar e postar de verdade.',
    ageLabel: '7+',
    durationLabel: '10–15 min',
    materialLabel: 'Caneta e tesoura',
    preview: '/activity-examples/postcard-real.webp',
  },
  {
    type: 'passport_stamp',
    category: 'writing',
    label: 'Passaporte de viagem',
    description: 'Uma página por país, com moldura para colar o bilhete ou o carimbo real.',
    ageLabel: 'Todas',
    durationLabel: '5 min',
    materialLabel: 'Cola e caneta',
    preview: '/activity-examples/passport-real.webp',
  },
  {
    type: 'travel_diary',
    category: 'writing',
    label: 'Diário do dia',
    description:
      'Melhor momento, a surpresa do dia, uma palavra nova aprendida e a nota da criança.',
    ageLabel: '8+',
    durationLabel: '10–15 min',
    materialLabel: 'Caneta',
    preview: '/activity-examples/travel-diary-real.webp',
  },
  {
    type: 'newspaper_headline',
    category: 'writing',
    label: 'Manchete do jornal',
    description: 'A criança vira repórter do ponto turístico e escreve a manchete da visita.',
    ageLabel: '9+',
    durationLabel: '10–15 min',
    materialLabel: 'Caneta',
    preview: '/activity-examples/newspaper-headline-real.webp',
  },
  {
    type: 'here_vs_home',
    category: 'writing',
    label: 'Aqui e na minha rua',
    description: 'Compara as ruas e as casas do destino com a rua onde a criança mora.',
    ageLabel: '8+',
    durationLabel: '10–15 min',
    materialLabel: 'Caneta',
    preview: '/activity-examples/here-vs-home-real.webp',
  },
];

/**
 * Países com guia de frases conferido. Sem isso na lista, o backend recusa a
 * atividade — então nem oferecemos o card, em vez de deixar a família escolher
 * uma página que não vai existir.
 */
export const PHRASEBOOK_COUNTRIES = new Set([
  'franca', 'france', 'belgica',
  'reino unido', 'inglaterra', 'united kingdom', 'escocia', 'irlanda',
  'estados unidos', 'united states', 'canada', 'australia', 'nova zelandia',
  'espanha', 'spain', 'argentina', 'chile', 'uruguai', 'mexico', 'peru', 'colombia',
  'italia', 'italy',
  'alemanha', 'germany', 'austria', 'suica',
  'japao', 'japan',
]);

const withoutAccents = (value) =>
  String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();

export const countryHasPhrasebook = (country) =>
  PHRASEBOOK_COUNTRIES.has(withoutAccents(country));

export const activityOptionsForCountry = (country) =>
  LANDMARK_ACTIVITY_OPTIONS.filter(
    (option) => option.type !== 'language_survival' || countryHasPhrasebook(country),
  );

export const activityOptionsByCategory = (options = LANDMARK_ACTIVITY_OPTIONS) =>
  ACTIVITY_CATEGORIES.map((category) => ({
    ...category,
    options: options.filter((option) => option.category === category.id),
  })).filter((category) => category.options.length > 0);

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
