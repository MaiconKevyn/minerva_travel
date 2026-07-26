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

// Limites afrouxados para a fase de desenvolvimento. Precisam bater com
// MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK e MAX_OPTIONAL_ACTIVITY_PAGES_PER_GUIDE
// no backend — o contrato de limites é verificado em teste.
export const MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK = 10;
export const MAX_OPTIONAL_ACTIVITIES_PER_GUIDE = 30;

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
    about:
      'A criança olha para a ilustração do lugar e marca cada detalhe da lista conforme encontra. Feita para ser resolvida em pé, durante a visita, sem precisar de mesa.',
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
    about:
      'Cada criança da família recebe uma pista e uma missão próprias, escritas para a idade dela e para aquele ponto turístico. As missões pedem observação e nunca tocar em nada ou se afastar dos adultos.',
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
    about:
      'Uma grade de letras com o nome do ponto turístico, da cidade e do país escondidos na horizontal e na vertical. A lista embaixo diz quais palavras procurar.',
    gallery: [
      { src: '/activity-examples/word-search-real.webp', label: 'Em branco', caption: 'A folha como a criança recebe.' },
      { src: '/activity-examples/word-search-solved.webp', label: 'Resolvida', caption: 'As palavras riscadas em vermelho, como fica depois de resolvida.' },
    ],
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
    about:
      'Um labirinto com um único caminho certo entre a criança e o ponto turístico. A grade cresce com a idade: curta para os menores, com becos sem saída de verdade para os maiores.',
    gallery: [
      { src: '/activity-examples/maze-real.webp', label: 'Em branco', caption: 'A folha como a criança recebe.' },
      { src: '/activity-examples/maze-solved.webp', label: 'Resolvida', caption: 'O caminho certo do A até o ponto turístico.' },
    ],
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
    about:
      'Os números seguem o contorno do próprio ponto turístico. Ligando na ordem, a silhueta do lugar aparece — a mesma que a criança viu na página anterior.',
    gallery: [
      { src: '/activity-examples/dot-to-dot-real.webp', label: 'Em branco', caption: 'A folha como a criança recebe.' },
      { src: '/activity-examples/dot-to-dot-solved.webp', label: 'Resolvida', caption: 'Os pontos ligados: a silhueta do lugar aparece.' },
    ],
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
    about:
      'Os nomes do lugar, da cidade e do país aparecem embaralhados, com uma caixinha por letra e a primeira já preenchida, que é onde a palavra mais longa costuma travar.',
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
    about:
      'Palavras cruzadas de verdade, com interseções e numeração. Todas as dicas são sobre a viagem, então a criança confere a resposta voltando uma página do guia.',
    gallery: [
      { src: '/activity-examples/crossword-real.webp', label: 'Em branco', caption: 'A folha como a criança recebe.' },
      { src: '/activity-examples/crossword-solved.webp', label: 'Resolvida', caption: 'A grade preenchida com todas as respostas.' },
    ],
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
    about:
      'Uma frase verdadeira sobre o lugar aparece cifrada em números. Três letras vêm reveladas para começar, e no fim há espaço para escrever a frase inteira.',
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
    gallery: [
      {
        src: '/activity-examples/spot-the-difference-real.webp',
        label: 'A página',
        caption: 'A folha como a criança recebe, com a lista para marcar.',
      },
      {
        src: '/activity-examples/spot-the-difference-scene-1.webp',
        label: 'Cena 1',
        caption: 'O primeiro desenho inteiro, do jeito que sai impresso.',
      },
      {
        src: '/activity-examples/spot-the-difference-scene-2.webp',
        label: 'Cena 2',
        caption: 'O segundo desenho inteiro: as diferenças estão aqui.',
      },
    ],
    about:
      'Dois desenhos do mesmo lugar com pequenas diferenças. Elas são conferidas uma a uma antes da impressão, e a página só diz o número que realmente existe.',
    category: 'puzzle',
    label: 'Ache os erros',
    description: 'Dois desenhos do lugar; a página conta as diferenças conferidas antes de imprimir.',
    ageLabel: '6+',
    durationLabel: '10–15 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/spot-the-difference-real.webp',
  },
  {
    type: 'coloring',
    about:
      'O ponto turístico em traço limpo, com formas grandes e sem detalhes miúdos, do jeito que uma criança consegue pintar sem sair da linha.',
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
    about:
      'A foto que vocês enviaram vira um desenho da família de férias no ponto turístico, pronto para colorir. A foto original nunca é impressa.',
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
    about:
      'Uma moldura com o lugar em miniatura e uma tela grande em branco no meio, para a criança pintar do jeito dela. Tem espaço para dar título e data à pintura.',
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
    about:
      'Cinco frases do idioma do país — cumprimentar, agradecer, pedir um sorvete, achar o banheiro e se apresentar — com a pronúncia escrita do jeito que se lê em português.',
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
    about:
      'A frente traz a arte do ponto turístico e o verso vem formatado como cartão de verdade: mensagem, remetente, caixa de selo e linhas de endereço, com linha de corte para postar.',
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
    about:
      'Uma página por país, com o nome da criança, a data de chegada e uma moldura tracejada do tamanho de um bilhete de entrada para colar.',
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
    about:
      'Três perguntas para fechar o dia: o melhor momento, o que surpreendeu na cidade e uma palavra nova aprendida. As pautas são largas, do tamanho de caderno escolar.',
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
    about:
      'A criança vira repórter daquele ponto turístico: escreve a manchete, conta o que aconteceu na visita e quem estava junto.',
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
    about:
      'Uma comparação entre as ruas e as casas do destino e a rua onde a criança mora, mais uma coisa que existe lá e não existe aqui.',
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

/**
 * Imagens que a lupa mostra. Sem galeria declarada, a própria miniatura é a
 * única página que existe — o modal continua útil porque ali ela aparece
 * inteira, e não só o topo recortado em 3:2.
 */
export const activityGallery = (activity) =>
  activity.gallery?.length
    ? activity.gallery
    : [
        {
          src: activity.preview,
          label: 'A página',
          caption: 'A folha como sai impressa no guia.',
        },
      ];

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

/**
 * O plano visto por ponto turístico, para a família conferir a distribuição.
 *
 * O catálogo é escolhido por atividade ("quero uma página de colorir"), mas o
 * que sai impresso é por parada — sem esta visão, ninguém percebe que deixou
 * um ponto sem nada e empilhou seis no primeiro.
 */
export const activityPlanByLandmark = (selections = [], landmarks = []) =>
  landmarks.map((landmark) => {
    const selectionId = landmark.selection_id || landmark.id;
    const chosen = selections
      .filter((selection) => selection.landmark_selection_id === selectionId)
      .map((selection) =>
        LANDMARK_ACTIVITY_OPTIONS.find((option) => option.type === selection.activity_type),
      )
      .filter(Boolean);
    return { landmark, selectionId, activities: chosen };
  });

export const landmarksWithActivity = (selections = [], activityType = '') =>
  selections
    .filter((selection) => selection.activity_type === activityType)
    .map((selection) => selection.landmark_selection_id);
