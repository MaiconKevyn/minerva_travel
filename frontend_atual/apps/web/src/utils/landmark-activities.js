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
    description:
      'Faz a criança olhar de verdade para o lugar em vez de passar batido. Cada detalhe achado vira uma lembrança que ela conta depois.',
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
      'Cada criança recebe uma pista e uma missão só dela, adaptada à idade e ao ponto turístico. Observar de perto é o que faz o lugar grudar na memória.',
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
    description:
      'Os nomes do lugar, da cidade e do país escondidos na grade. Procurando letra por letra, a criança aprende a escrever os nomes sem perceber.',
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
    description:
      'Um caminho só até o ponto turístico, e é ela quem tem de achar. Preenche o tempo da fila e ainda treina paciência.',
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
    description:
      'A silhueta do lugar aparece aos poucos, número a número. No fim ela reconhece o monumento que viu de verdade — e a ficha cai.',
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
    description:
      'Os nomes da viagem embaralhados, com a primeira letra de dica. Desembaralhar fixa o nome do lugar de um jeito que só ler não fixa.',
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
    description:
      'As dicas falam da cidade, do país e do ponto turístico. Para completar, a criança precisa lembrar do que viu: vira revisão sem parecer lição.',
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
    description:
      'Uma frase verdadeira sobre o lugar escondida atrás de uma chave numérica. Decifrar dá a sensação de descobrir um segredo do monumento.',
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
    description:
      'Dois desenhos quase iguais do mesmo lugar. Comparar treina o olhar para os detalhes da arquitetura que ela acabou de ver de perto.',
    ageLabel: '6+',
    durationLabel: '10–15 min',
    materialLabel: 'Lápis',
    preview: '/activity-examples/spot-the-difference-real.webp',
  },
  {
    type: 'coloring',
    about:
      'O ponto turístico em traço limpo, com formas grandes e sem detalhes miúdos, do jeito que uma criança consegue pintar sem sair da linha. Embaixo do desenho sai uma frase escrita para aquela família e aquela parada, para ela colorir também.',
    category: 'art',
    label: 'Página para colorir',
    description:
      'O monumento em traços limpos, formas grandes e uma frase personalizada impressa junto. Pintar devagar é o que transforma o passeio em lembrança dela.',
    ageLabel: '4+',
    durationLabel: '15–25 min',
    materialLabel: 'Lápis de cor',
    preview: '/activity-examples/coloring-real.webp',
  },
  {
    type: 'family_coloring',
    about:
      'A família vira um desenho de férias no ponto turístico, pronto para colorir. Quando vocês enviam a foto, ela serve só de referência para o traço e nunca é impressa; sem foto, a cena sai do mesmo jeito, sem semelhança com ninguém real.',
    category: 'art',
    label: 'Família de férias para colorir',
    description:
      'A família vira um desenho de férias no ponto turístico — a foto enviada como referência nunca é impressa. A criança se vê dentro da viagem.',
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
    description:
      'Uma folha em branco para a criança criar uma pintura do lugar do jeito dela. Sem gabarito: o que sai é a versão que ela viu.',
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
    description:
      'Cinco frases para a criança pedir sozinha, com a pronúncia escrita do jeito que se fala. Falar a primeira palavra em outra língua é um momento que não se esquece.',
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
    description:
      'Frente ilustrada e verso para escrever de verdade. Escrever para alguém obriga a resumir a viagem — e o cartão chega em casa antes da família.',
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
    description:
      'Uma página por país para colar o bilhete, o carimbo, o que sobrou do bolso. Vira o álbum da viagem montado pela própria criança.',
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
      'Melhor momento, a surpresa do dia, uma palavra nova. Escrever obriga a criança a escolher o que valeu mais — e a dizer o que ela quer repetir na próxima viagem.',
    ageLabel: '8+',
    durationLabel: '10–15 min',
    materialLabel: 'Caneta',
    preview: '/activity-examples/travel-diary-real.webp',
  },
  {
    type: 'newspaper_headline',
    about:
      'A criança vira repórter daquele ponto turístico: escreve a manchete, assina a reportagem, conta o que aconteceu na visita, quem estava junto e o que mais chamou a atenção — com espaço para desenhar a foto que ilustraria a notícia.',
    category: 'writing',
    label: 'Manchete do jornal',
    description:
      'A criança vira repórter e escreve a manchete da visita. Contar como notícia faz ela reparar no que era mesmo digno de nota.',
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
    description:
      'Compara a rua do destino com a rua de casa. É o exercício que mostra para a criança que existe mais de um jeito de viver.',
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
/**
 * Pa\u00eds \u2192 idioma conferido, espelho de `x-minerva-flight-vocabulary-languages`.
 *
 * A tela precisa dizer de qual idioma ser\u00e3o as palavras antes de gerar nada,
 * ent\u00e3o a lista vive aqui tamb\u00e9m. Um teste de contrato compara os dois: sem
 * ele, a tela prometeria um idioma que o guia n\u00e3o sabe imprimir.
 */
export const FLIGHT_VOCABULARY_LANGUAGES = {
  alemanha: 'alem\u00e3o', argentina: 'espanhol', australia: 'ingl\u00eas', austria: 'alem\u00e3o',
  belgica: 'franc\u00eas', canada: 'ingl\u00eas', chile: 'espanhol', colombia: 'espanhol',
  escocia: 'ingl\u00eas', espanha: 'espanhol', 'estados unidos': 'ingl\u00eas', franca: 'franc\u00eas',
  france: 'franc\u00eas', germany: 'alem\u00e3o', inglaterra: 'ingl\u00eas', irlanda: 'ingl\u00eas',
  italia: 'italiano', italy: 'italiano', japan: 'japon\u00eas', japao: 'japon\u00eas',
  mexico: 'espanhol', 'nova zelandia': 'ingl\u00eas', peru: 'espanhol', 'reino unido': 'ingl\u00eas',
  spain: 'espanhol', suica: 'alem\u00e3o', 'united kingdom': 'ingl\u00eas', 'united states': 'ingl\u00eas',
  uruguai: 'espanhol',
};

export const PHRASEBOOK_COUNTRIES = new Set(Object.keys(FLIGHT_VOCABULARY_LANGUAGES));

const withoutAccents = (value) =>
  String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();

export const countryHasPhrasebook = (country) =>
  PHRASEBOOK_COUNTRIES.has(withoutAccents(country));

export const flightVocabularyLanguage = (country) =>
  FLIGHT_VOCABULARY_LANGUAGES[withoutAccents(country)] || '';

export const countryHasFlightVocabulary = (country) => Boolean(flightVocabularyLanguage(country));

/**
 * Os pa\u00edses que ganham p\u00e1gina de palavras, na ordem em que a fam\u00edlia visita \u2014
 * a mesma ordem em que as p\u00e1ginas saem impressas.
 */
export const guideFlightVocabularyCountries = (landmarks = []) => {
  const seen = new Map();
  landmarks.forEach((landmark) => {
    const country = String(landmark?.country || '').trim();
    const language = flightVocabularyLanguage(country);
    if (language && !seen.has(withoutAccents(country))) {
      seen.set(withoutAccents(country), { country, language });
    }
  });
  return [...seen.values()];
};

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
