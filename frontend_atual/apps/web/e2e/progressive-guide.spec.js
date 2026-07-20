import { expect, test } from '@playwright/test';
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
});

test('family reviews pages and controls family inclusion on a landmark', async ({
  page,
}) => {
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

  const sessionPayload = () => ({
    session_id: 'syntheticsession',
    created_at: '2026-07-20T00:00:00+00:00',
    expires_at: '2026-08-03T00:00:00+00:00',
    title: 'Família Aurora',
    active_page_id: !coverApproved
      ? 'cover'
      : !summaryApproved
        ? 'summary'
        : !landmarkApproved
          ? 'landmark-1'
          : null,
    is_complete: coverApproved && summaryApproved && landmarkApproved,
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
      }),
    ],
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
            current_step: 6,
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
    return route.abort('failed');
  });
  await page.route('**/guide-builder/syntheticsession/assets/*.png', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: onePixelPng }),
  );

  const email = `paginas-${test.info().project.name}@example.test`;
  const password = 'Aventura2026';
  await page.goto('/signup');
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
  await page.goto('/create');

  await page.getByRole('button', { name: 'Começar pelas páginas' }).click();
  await expect(page.getByText('Nenhuma imagem gerada ainda')).toBeVisible();
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await expect(page.getByAltText('Versão escolhida de Capa da família')).toBeVisible();
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
  await page.getByRole('button', { name: 'Aprovar e continuar' }).click();

  await expect(page.getByRole('heading', { name: 'Nosso roteiro ilustrado' })).toBeVisible();
  await expect(page.getByText('Torre Eiffel', { exact: true })).toBeVisible();
  await expect(page.getByText('Coliseu', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await page.getByRole('button', { name: 'Aprovar e continuar' }).click();

  await expect(page.getByRole('heading', { name: 'Torre Eiffel, França' })).toBeVisible();
  const includeFamilySwitch = page.getByRole('switch', { name: 'Incluir família' });
  await expect(includeFamilySwitch).not.toBeChecked();
  await page.getByRole('button', { name: 'Gerar página' }).click();
  await expect(page.getByText('Sem família', { exact: true })).toBeVisible();
  await includeFamilySwitch.click();
  await expect(includeFamilySwitch).toBeChecked();
  await page.getByRole('button', { name: 'Gerar outra versão' }).click();
  await expect(page.getByText('Com família', { exact: true })).toBeVisible();
  expect(landmarkFamilyRequests).toEqual([false, true]);
  await page.getByRole('button', { name: 'Aprovar e continuar' }).click();
  await page.getByRole('button', { name: 'Concluir revisão das imagens' }).click();

  await expect(page.getByRole('heading', { name: 'Páginas aprovadas!' })).toBeVisible();
  await expect(page.getByText(/Nenhum PDF foi gerado/)).toBeVisible();
  expect(consoleErrors).toEqual([]);
  await test.info().attach(`progressive-guide-${test.info().project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  });
});
