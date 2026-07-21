import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { Buffer } from 'node:buffer';

const onePixelPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF/gL+XzrPAAAAAElFTkSuQmCC',
  'base64',
);

const attempt = (id, filename, revisionInstruction = '', includeFamily = false) => ({
  id,
  asset_url: `/guide-builder/syntheticsession/assets/${filename}`,
  created_at: '2026-07-20T00:00:00+00:00',
  revision_instruction: revisionInstruction,
  include_family: includeFamily,
});

const pageState = ({
  id,
  kind,
  title,
  position,
  requiredCopy,
  attempts = [],
  selectedAttemptId = null,
  approved = false,
  metadata = {},
}) => ({
  id,
  kind,
  title,
  position,
  status: approved ? 'approved' : attempts.length ? 'awaiting_approval' : 'ready',
  required_copy: requiredCopy,
  attempts,
  selected_attempt_id: selectedAttemptId,
  attempts_left: 4 - attempts.length,
  approved_at: approved ? '2026-07-20T00:01:00+00:00' : null,
  error: null,
  metadata,
});

test('restored activity step keeps the no-optional path and mandatory memory visible', async ({ page }) => {
  await page.route('**/api/guides', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"guides":[]}' }),
  );
  await page.route('**/api/drafts/current', (route) =>
    route.fulfill({
      status: 200,
      json: {
        draft: {
          id: 'activity-draft',
          revision: 1,
          payload: {
            current_step: 5,
            family_name: 'Aurora',
            destination: 'Paris em Julho de 2026',
            destinations_list: [
              { id: 'paris', place: 'Paris', timing: 'Julho de 2026', days: 3, landmarks: ['Torre Eiffel'] },
            ],
            itinerary_mode: 'known',
            children_list: [{ id: 'child-1', name: 'Lia', age: 8 }],
            parents_list: ['Ana', 'Caio'],
            year: 2026,
            parsed_data: {
              destinations: [{ id: 'paris', city: 'Paris', country: 'França' }],
              landmarks: [
                {
                  id: 'eiffel-card',
                  selection_id: 'paris:eiffel',
                  destination_id: 'paris',
                  name: 'Torre Eiffel',
                  city: 'Paris',
                  country: 'França',
                },
              ],
            },
            selected_landmarks: ['paris:eiffel'],
            landmark_activity_selections: [],
            itinerary_preferences: { days: 3, interests: [], pace: 'balanced' },
            has_searched_landmarks: true,
          },
        },
      },
    }),
  );
  await page.route('**/api/drafts/activity-draft', (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: 'activity-draft',
        revision: 2,
        payload: route.request().postDataJSON()?.payload || {},
      },
    }),
  );

  const email = `atividades-${test.info().project.name}@example.test`;
  const password = 'Aventura2026';
  await page.goto('/signup', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Nome da Família ou Responsável').fill('Família Aurora');
  await page.getByLabel('Email Mágico').fill(email);
  await page.getByLabel('Senha Secreta', { exact: true }).fill(password);
  await page.getByLabel('Confirme a Senha').fill(password);
  await page.getByRole('button', { name: 'Criar Minha Conta' }).click();
  await expect(page).toHaveURL(/\/login$/);
  const loginEmail = page.getByLabel('Email Mágico');
  const loginPassword = page.getByLabel('Senha Secreta');
  await loginPassword.fill(password);
  await loginEmail.fill(email);
  await expect(loginEmail).toHaveValue(email);
  await expect(loginPassword).toHaveValue(password);
  await page.getByRole('button', { name: 'Entrar na Aventura' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/create', { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Atividades da aventura' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Minha melhor memória' })).toBeVisible();
  await expect(page.getByText('0 de 8 páginas opcionais')).toBeVisible();
  await page.getByRole('button', { name: 'Continuar sem atividades opcionais' }).click();
  await expect(page.getByRole('heading', { name: /Escolha a foto de capa do PDF/ })).toBeVisible();
});

test('family reviews pages and controls family inclusion on a landmark', async ({
  page,
}) => {
  test.setTimeout(60_000);
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  let coverAttempts = [];
  const coverRevisionRequests = [];
  let rejectNextCoverRevision = false;
  let coverSelected = null;
  let coverApproved = false;
  let summaryAttempts = [];
  let summarySelected = null;
  let summaryApproved = false;
  let landmarkAttempts = [];
  const landmarkFamilyRequests = [];
  let landmarkSelected = null;
  let landmarkApproved = false;
  const activityAttempts = { coloring: [], word_search: [] };
  const activitySelected = { coloring: null, word_search: null };
  const activityApproved = { coloring: false, word_search: false };
  const activityRequestBodies = [];
  let wordSearchIncluded = false;
  let layoutRevision = 0;
  let memoryAttempts = [];
  let memorySelected = null;
  let memoryApproved = false;
  let pdfExportRequests = 0;
  let sessionRevision = 0;

  const sessionPayload = () => ({
    session_id: 'syntheticsession',
    created_at: '2026-07-20T00:00:00+00:00',
    expires_at: '2026-08-03T00:00:00+00:00',
    title: 'Família Aurora',
    revision: ++sessionRevision,
    layout_revision: layoutRevision,
    active_page_id: !coverApproved
      ? 'cover'
      : !summaryApproved
        ? 'summary'
        : !landmarkApproved
          ? 'landmark-1'
          : !activityApproved.coloring
            ? 'activity-coloring'
          : wordSearchIncluded && !activityApproved.word_search
              ? 'activity-word-search'
              : !memoryApproved
                ? 'best-memory'
                : null,
    is_complete: coverApproved && summaryApproved && landmarkApproved &&
      activityApproved.coloring && (!wordSearchIncluded || activityApproved.word_search) && memoryApproved,
    pages: [
      pageState({
        id: 'cover',
        kind: 'cover',
        title: 'Capa da família',
        position: 1,
        requiredCopy: ['Família Aurora', 'Julho de 2026'],
        attempts: coverAttempts,
        selectedAttemptId: coverSelected,
        approved: coverApproved,
      }),
      pageState({
        id: 'summary',
        kind: 'trip_summary',
        title: 'Nosso roteiro ilustrado',
        position: 2,
        requiredCopy: [
          'Nosso roteiro',
          'Família Aurora',
          'Julho de 2026',
          'Torre Eiffel',
          'Coliseu',
        ],
        attempts: summaryAttempts,
        selectedAttemptId: summarySelected,
        approved: summaryApproved,
      }),
      pageState({
        id: 'landmark-1',
        kind: 'landmark',
        title: 'Torre Eiffel, França',
        position: 3,
        requiredCopy: ['Torre Eiffel', 'Paris, França', 'Família Aurora • Julho de 2026'],
        attempts: landmarkAttempts,
        selectedAttemptId: landmarkSelected,
        approved: landmarkApproved,
        metadata: { landmark_selection_id: 'eiffel', landmark_name: 'Torre Eiffel' },
      }),
      pageState({
        id: 'activity-coloring',
        kind: 'landmark_activity',
        title: 'Página para colorir — Torre Eiffel',
        position: 4,
        requiredCopy: ['Torre Eiffel', 'Pinte sua aventura!'],
        attempts: activityAttempts.coloring,
        selectedAttemptId: activitySelected.coloring,
        approved: activityApproved.coloring,
        metadata: {
          activity_type: 'coloring',
          activity_label: 'Página para colorir',
          landmark_selection_id: 'eiffel',
          landmark_name: 'Torre Eiffel',
          linked_landmark_page_id: 'landmark-1',
        },
      }),
      pageState({
        id: 'activity-word-search',
        kind: 'landmark_activity',
        title: 'Caça-palavras — Torre Eiffel',
        position: 5,
        requiredCopy: ['Torre Eiffel', 'Encontre as palavras'],
        attempts: activityAttempts.word_search,
        selectedAttemptId: activitySelected.word_search,
        approved: activityApproved.word_search,
        metadata: {
          activity_type: 'word_search',
          activity_label: 'Caça-palavras',
          landmark_selection_id: 'eiffel',
          landmark_name: 'Torre Eiffel',
          linked_landmark_page_id: 'landmark-1',
        },
      }),
      pageState({
        id: 'best-memory',
        kind: 'best_memory',
        title: 'Minha melhor memória',
        position: 6,
        requiredCopy: ['Minha melhor memória', 'O que eu mais gostei', 'Data'],
        attempts: memoryAttempts,
        selectedAttemptId: memorySelected,
        approved: memoryApproved,
        metadata: { age_complexity: 'early_reader' },
      }),
    ].filter((item) => wordSearchIncluded || item.id !== 'activity-word-search'),
  });

  await page.route('**/api/guides', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"guides":[]}' }),
  );
  await page.route('**/api/drafts/current', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        draft: {
          id: 'visual-draft',
          revision: 1,
          payload: {
            current_step: 7,
            family_name: 'Aurora',
            destination: 'Paris e Roma em Julho de 2026',
            destinations_list: [
              {
                id: 'trip-1',
                place: 'Paris e Roma',
                timing: 'Julho de 2026',
                days: 5,
                landmarks: ['Torre Eiffel', 'Coliseu'],
              },
            ],
            itinerary_mode: 'known',
            children_list: [{ id: 'child-1', name: 'Lia', age: 8 }],
            parents_list: ['Ana', 'Caio'],
            year: 2026,
            parsed_data: {
              destinations: [{ id: 'europe', city: 'Paris e Roma', country: 'Europa' }],
              landmarks: [
                { id: 'eiffel', destination_id: 'europe', name: 'Torre Eiffel' },
                { id: 'colosseum', destination_id: 'europe', name: 'Coliseu' },
              ],
            },
            selected_landmarks: ['eiffel', 'colosseum'],
            landmark_activity_selections: [
              { landmark_selection_id: 'eiffel', activity_type: 'coloring', order: 1 },
              { landmark_selection_id: 'eiffel', activity_type: 'word_search', order: 2 },
            ],
            itinerary_preferences: { days: 5, interests: [], pace: 'balanced' },
            has_searched_landmarks: true,
          },
        },
      }),
    }),
  );
  await page.route('**/api/drafts/visual-draft', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'visual-draft',
        revision: 2,
        payload: route.request().postDataJSON()?.payload || {},
      }),
    }),
  );
  await page.route('**/api/guide-builder**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    if (url.pathname === '/api/guide-builder' && method === 'POST') {
      return route.fulfill({ status: 201, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/activities') && method === 'POST') {
      expect(request.postDataJSON()).toMatchObject({
        landmark_selection_id: 'eiffel',
        activity_type: 'word_search',
        layout_revision: 0,
      });
      wordSearchIncluded = true;
      layoutRevision += 1;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/cover/attempts') && method === 'POST') {
      const revisionInstruction = request.postDataJSON()?.revision_instruction || '';
      coverRevisionRequests.push(revisionInstruction);
      if (rejectNextCoverRevision) {
        rejectNextCoverRevision = false;
        return route.fulfill({
          status: 502,
          json: { detail: { message: 'Falha simulada ao refazer a capa.' } },
        });
      }
      const next = coverAttempts.length + 1;
      coverAttempts = [
        ...coverAttempts,
        attempt(`cover-${next}`, `cover-${next}.png`, revisionInstruction),
      ];
      coverSelected = `cover-${next}`;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/cover/selection') && method === 'PATCH') {
      coverSelected = request.postDataJSON().attempt_id;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/cover/approve') && method === 'POST') {
      coverSelected = request.postDataJSON().attempt_id;
      coverApproved = true;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/summary/attempts') && method === 'POST') {
      summaryAttempts = [attempt('summary-1', 'summary-1.png')];
      summarySelected = 'summary-1';
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/summary/approve') && method === 'POST') {
      summaryApproved = true;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/landmark-1/attempts') && method === 'POST') {
      const requestPayload = request.postDataJSON() || {};
      const includeFamily = requestPayload.include_family === true;
      landmarkFamilyRequests.push(includeFamily);
      const next = landmarkAttempts.length + 1;
      if (next === 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      landmarkAttempts = [
        ...landmarkAttempts,
        attempt(
          `landmark-1-${next}`,
          `landmark-1-${next}.png`,
          requestPayload.revision_instruction || '',
          includeFamily,
        ),
      ];
      landmarkSelected = `landmark-1-${next}`;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/landmark-1/approve') && method === 'POST') {
      landmarkSelected = request.postDataJSON().attempt_id;
      landmarkApproved = true;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    for (const [activityKey, pageId] of [
      ['coloring', 'activity-coloring'],
      ['word_search', 'activity-word-search'],
    ]) {
      if (url.pathname.endsWith(`/pages/${pageId}/attempts`) && method === 'POST') {
        const requestPayload = request.postDataJSON() || {};
        activityRequestBodies.push(requestPayload);
        activityAttempts[activityKey] = [
          attempt(`${pageId}-1`, `${pageId}-1.png`, requestPayload.revision_instruction || ''),
        ];
        activitySelected[activityKey] = `${pageId}-1`;
        return route.fulfill({ status: 200, json: sessionPayload() });
      }
      if (url.pathname.endsWith(`/pages/${pageId}/approve`) && method === 'POST') {
        activityApproved[activityKey] = true;
        return route.fulfill({ status: 200, json: sessionPayload() });
      }
    }
    if (url.pathname.endsWith('/pages/best-memory/attempts') && method === 'POST') {
      const requestPayload = request.postDataJSON() || {};
      activityRequestBodies.push(requestPayload);
      memoryAttempts = [attempt('best-memory-1', 'best-memory-1.png')];
      memorySelected = 'best-memory-1';
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/pages/best-memory/approve') && method === 'POST') {
      memoryApproved = true;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (url.pathname.endsWith('/complete') && method === 'POST') {
      return route.fulfill({
        status: 200,
        json: {
          session_id: 'syntheticsession',
          pages: sessionPayload().pages.map((item) => ({
            page_id: item.id,
            attempt_id: item.selected_attempt_id,
          })),
        },
      });
    }
    if (url.pathname.endsWith('/pdf') && method === 'POST') {
      pdfExportRequests += 1;
      if (pdfExportRequests === 1) {
        return route.fulfill({
          status: 503,
          json: {
            detail: {
              code: 'approved_page_pdf_failed',
              message: 'Não foi possível montar o PDF. Tente novamente.',
            },
          },
        });
      }
      return route.fulfill({
        status: 200,
        json: {
          session_id: 'syntheticsession',
          download_url: '/guide-builder/syntheticsession/pdf',
          filename: 'familia-aurora-minerva-travel.pdf',
          page_count: 6,
        },
      });
    }
    return route.abort('failed');
  });
  await page.route('**/guide-builder/syntheticsession/assets/*.png', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: onePixelPng }),
  );
  await page.route('**/guide-builder/syntheticsession/pdf', (route) => {
    if (new URL(route.request().url()).pathname.startsWith('/api/')) {
      return route.fallback();
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/pdf',
      headers: {
        'Content-Disposition': 'attachment; filename="familia-aurora-minerva-travel.pdf"',
      },
      body: Buffer.from('%PDF-synthetic'),
    });
  });

  const email = `paginas-${test.info().project.name}@example.test`;
  const password = 'Aventura2026';
  await page.goto('/signup', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Nome da Família ou Responsável').fill('Família Aurora');
  await page.getByLabel('Email Mágico').fill(email);
  await page.getByLabel('Senha Secreta', { exact: true }).fill(password);
  await page.getByLabel('Confirme a Senha').fill(password);
  await page.getByRole('button', { name: 'Criar Minha Conta' }).click();
  await expect(page).toHaveURL(/\/login$/);
  const loginEmail = page.getByLabel('Email Mágico');
  const loginPassword = page.getByLabel('Senha Secreta');
  await loginPassword.fill(password);
  await loginEmail.fill(email);
  await expect(loginEmail).toHaveValue(email);
  await expect(loginPassword).toHaveValue(password);
  await page.getByRole('button', { name: 'Entrar na Aventura' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/create', { waitUntil: 'domcontentloaded' });

  await page.getByRole('button', { name: 'Começar pelas páginas' }).click();
  await expect(page.getByText('Nenhuma imagem gerada ainda')).toBeVisible();

  await page.getByRole('button', { name: 'Adicionar atividades' }).click();
  await expect(page.getByRole('heading', { name: 'Atividades do guia' })).toBeVisible();
  const familyColoringCard = page.locator('article').filter({
    hasText: 'Família de férias para colorir',
  });
  await expect(familyColoringCard).toBeVisible();
  await familyColoringCard.getByRole('button', { name: /Ver exemplo completo/ }).click();
  const familyColoringPreview = page.getByRole('dialog').filter({
    has: page.getByRole('heading', { name: 'Família de férias para colorir' }),
  });
  await expect(familyColoringPreview).toBeVisible();
  const familyPreviewImage = familyColoringPreview.getByAltText(
    'Exemplo completo da atividade Família de férias para colorir',
  );
  await expect(familyPreviewImage).toHaveAttribute(
    'src',
    '/activity-examples/family-coloring-real.webp',
  );
  expect(await familyPreviewImage.evaluate((image) => image.naturalWidth)).toBeGreaterThan(0);
  await familyColoringPreview.getByRole('button', { name: 'Close' }).click();
  const wordSearchCard = page.locator('article').filter({ hasText: 'Caça-palavras' });
  await wordSearchCard.getByRole('button', { name: /Ver exemplo completo/ }).click();
  const previewDialog = page.getByRole('dialog').filter({
    has: page.getByRole('heading', { name: 'Caça-palavras' }),
  });
  await expect(previewDialog).toBeVisible();
  await previewDialog.getByRole('button', { name: 'Close' }).click();
  await wordSearchCard.getByRole('button', { name: 'Adicionar ao guia' }).click();
  await expect(page.getByText('Atividade adicionada. Você pode posicioná-la ou gerar quando quiser.')).toBeVisible();
  await page.getByRole('button', { name: /Organizar páginas/ }).click();
  const activityPanel = page.getByRole('dialog').filter({
    has: page.getByRole('heading', { name: 'Atividades do guia' }),
  });
  await expect(activityPanel.getByText('Caça-palavras — Torre Eiffel', { exact: true })).toBeVisible();
  await expect(activityPanel.getByLabel('Inserir Caça-palavras — Torre Eiffel depois de')).toBeVisible();
  const panelAccessibility = await new AxeBuilder({ page })
    .include('[role="dialog"]')
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  expect(panelAccessibility.violations).toEqual([]);
  await activityPanel.getByRole('button', { name: 'Close' }).click();

  await page.getByRole('button', { name: /Torre Eiffel, França/ }).click();
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await expect(page.getByRole('button', { name: 'Gerando esta página...' })).toBeVisible();
  await page.getByRole('button', { name: /Capa da família/ }).click();
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await expect(page.getByAltText('Versão escolhida de Capa da família')).toBeVisible();
  await page.getByRole('button', { name: /Torre Eiffel, França/ }).click();
  await expect(page.getByAltText('Versão escolhida de Torre Eiffel, França')).toBeVisible();
  await expect(page.getByText('Sem família', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Capa da família/ }).click();
  const revisionField = page.getByLabel('O que você quer mudar nesta versão?');
  await expect(revisionField).toBeVisible();
  await revisionField.fill('Mude para animação 3D, com tons azuis e título menor.');
  await page.getByRole('button', { name: 'Gerar versão com ajustes' }).click();
  await expect(page.getByText('Versão 2', { exact: true })).toBeVisible();
  await expect(revisionField).toHaveValue('');
  expect(coverRevisionRequests).toEqual([
    '',
    'Mude para animação 3D, com tons azuis e título menor.',
  ]);
  rejectNextCoverRevision = true;
  await revisionField.fill('Troque apenas o fundo por uma cena noturna.');
  await page.getByRole('button', { name: 'Gerar versão com ajustes' }).click();
  await expect(page.getByText('Falha simulada ao refazer a capa.')).toBeVisible();
  await expect(revisionField).toHaveValue('Troque apenas o fundo por uma cena noturna.');
  expect(coverRevisionRequests.at(-1)).toBe(
    'Troque apenas o fundo por uma cena noturna.',
  );
  expect(consoleErrors.some((message) => message.includes('502 (Bad Gateway)'))).toBe(true);
  consoleErrors.length = 0;
  await page.locator('button').filter({ hasText: 'Versão 1' }).click();
  await page.getByRole('button', { name: 'Aprovar página' }).click();

  await expect(page.getByRole('heading', { name: 'Nosso roteiro ilustrado' })).toBeVisible();
  await expect(page.getByText('Torre Eiffel', { exact: true })).toBeVisible();
  await expect(page.getByText('Coliseu', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await page.getByRole('button', { name: 'Aprovar página' }).click();

  await expect(page.getByRole('heading', { name: 'Torre Eiffel, França' })).toBeVisible();
  const includeFamilySwitch = page.getByRole('switch', { name: 'Incluir família' });
  await expect(includeFamilySwitch).not.toBeChecked();
  await expect(page.getByText('Sem família', { exact: true })).toBeVisible();
  await includeFamilySwitch.click();
  await expect(includeFamilySwitch).toBeChecked();
  await page.getByRole('button', { name: 'Gerar outra versão' }).click();
  await expect(page.getByText('Com família', { exact: true })).toBeVisible();
  expect(landmarkFamilyRequests).toEqual([false, true]);
  await page.getByRole('button', { name: 'Aprovar página' }).click();

  await expect(page.getByRole('heading', { name: 'Página para colorir — Torre Eiffel' })).toBeVisible();
  await expect(page.getByText('Ligada a Torre Eiffel')).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Incluir família' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await page.getByRole('button', { name: 'Aprovar página' }).click();

  await expect(page.getByRole('heading', { name: 'Caça-palavras — Torre Eiffel' })).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Incluir família' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await page.getByRole('button', { name: 'Aprovar página' }).click();

  await expect(page.getByRole('heading', { name: 'Minha melhor memória' })).toBeVisible();
  await expect(page.locator('section span').getByText('Página obrigatória', { exact: true })).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Incluir família' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await page.getByRole('button', { name: 'Aprovar página' }).click();
  expect(activityRequestBodies).toHaveLength(3);
  expect(activityRequestBodies.every((body) => body.include_family === false)).toBe(true);
  await page.getByRole('button', { name: 'Ver páginas aprovadas' }).click();

  await expect(page.getByRole('heading', { name: 'Páginas aprovadas!' })).toBeVisible();
  await page.getByRole('button', { name: 'Gerar PDF e baixar' }).click();
  await expect(page.getByRole('alert')).toContainText('Não foi possível montar o PDF.');
  const firstDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Gerar PDF e baixar' }).click();
  expect((await firstDownload).suggestedFilename()).toBe('familia-aurora-minerva-travel.pdf');
  await expect(page.getByText('PDF pronto com 6 páginas.')).toBeVisible();
  const secondDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Baixar PDF novamente' }).click();
  expect((await secondDownload).suggestedFilename()).toBe('familia-aurora-minerva-travel.pdf');
  expect(pdfExportRequests).toBe(3);
  expect(consoleErrors).toEqual([
    expect.stringContaining('503 (Service Unavailable)'),
  ]);
  await test.info().attach(`progressive-guide-${test.info().project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  });
});
