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

const authenticateLocalTestUser = async (page, email, name) => {
  await page.addInitScript(({ userEmail, userName }) => {
    globalThis.localStorage.setItem('minerva_local_session', JSON.stringify({
      id: `local:${userEmail}`,
      email: userEmail,
      name: userName,
      collectionName: 'users',
    }));
  }, { userEmail: email, userName: name });
};

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
  await authenticateLocalTestUser(page, email, 'Família Aurora');
  await page.goto('/create', { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Atividades da aventura' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Minha melhor memória' })).toBeVisible();
  await expect(page.getByText('0 de 30 páginas opcionais')).toBeVisible();
  await page.getByRole('button', { name: 'Continuar sem atividades opcionais' }).click();
  await expect(page.getByRole('heading', { name: /Seu roteiro está pronto. Como você quer a capa?/ })).toBeVisible();
});

test('reload restores the saved builder session and its generated pages', async ({ page }) => {
  const builderSession = {
    session_id: 'resumesession123',
    created_at: '2026-07-21T10:00:00+00:00',
    expires_at: '2026-09-04T10:00:00+00:00',
    title: 'Família Aurora',
    revision: 5,
    layout_revision: 0,
    active_page_id: 'cover',
    is_complete: false,
    pages: [pageState({
      id: 'cover',
      kind: 'cover',
      title: 'Capa da família',
      position: 1,
      requiredCopy: ['Família Aurora', 'Julho de 2026'],
      attempts: [{
        ...attempt('cover-saved', 'cover-saved.png'),
        asset_url: '/guide-builder/resumesession123/assets/cover-saved.png',
      }],
      selectedAttemptId: 'cover-saved',
    })],
  };
  let builderGets = 0;
  let builderCreates = 0;

  await page.route('**/api/guides', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"guides":[]}' }),
  );
  await page.route('**/api/drafts/current', (route) =>
    route.fulfill({
      status: 200,
      json: {
        draft: {
          id: 'resume-draft',
          revision: 4,
          updated_at: '2026-07-21T10:02:00+00:00',
          payload: {
            schema_version: 2,
            current_step: 7,
            builder_session_id: 'resumesession123',
            family_name: 'Aurora',
            destination: 'Paris em Julho de 2026',
            destinations_list: [
              {
                id: 'paris',
                place: 'Paris',
                timing: 'Julho de 2026',
                days: 3,
                landmarks: ['Torre Eiffel'],
              },
            ],
            itinerary_mode: 'known',
            children_list: [{ id: 'child-1', name: 'Lia', age: 8 }],
            parents_list: ['Ana', 'Caio'],
            year: 2026,
            parsed_data: { destinations: [], landmarks: [] },
            selected_landmarks: [],
            landmark_activity_selections: [],
            itinerary_preferences: { days: 3, interests: [], pace: 'balanced' },
            has_searched_landmarks: true,
          },
        },
      },
    }),
  );
  await page.route('**/api/drafts/resume-draft', (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: 'resume-draft',
        revision: 5,
        updated_at: '2026-07-21T10:03:00+00:00',
        payload: route.request().postDataJSON()?.payload || {},
      },
    }),
  );
  await page.route(/\/api\/guide-builder(?:\/.*)?$/, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === '/api/guide-builder/resumesession123' && request.method() === 'GET') {
      builderGets += 1;
      if (builderGets > 1) {
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
      return route.fulfill({ status: 200, json: builderSession });
    }
    if (pathname === '/api/guide-builder' && request.method() === 'POST') {
      builderCreates += 1;
    }
    return route.abort('failed');
  });
  await page.route('**/guide-builder/resumesession123/assets/cover-saved.png', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: onePixelPng }),
  );

  const email = `retomada-${test.info().project.name}@example.test`;
  await authenticateLocalTestUser(page, email, 'Família Aurora');
  await page.goto('/create', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(/\/create\?builder=resumesession123$/);
  await expect(page.getByAltText('Preview da capa do guia')).toBeVisible();
  await expect(page.getByText('Progresso recuperado. Suas páginas geradas continuam salvas com segurança.')).toBeVisible();

  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Recuperando suas páginas…' })).toBeVisible();
  await expect(page.getByAltText('Preview da capa do guia')).toBeVisible();
  expect(builderGets).toBeGreaterThanOrEqual(2);
  expect(builderCreates).toBe(0);
});

test('expired builder returns to the photo step without erasing the saved itinerary', async ({ page }) => {
  let updatedPayload = null;
  await page.route('**/api/guides', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"guides":[]}' }),
  );
  await page.route('**/api/drafts/current', (route) =>
    route.fulfill({
      status: 200,
      json: {
        draft: {
          id: 'expired-draft',
          revision: 2,
          updated_at: '2026-07-21T10:00:00+00:00',
          payload: {
            schema_version: 2,
            current_step: 7,
            builder_session_id: 'expiredsession123',
            family_name: 'Silva',
            destination: 'Paris em Julho de 2026',
            destinations_list: [
              {
                id: 'paris',
                place: 'Paris',
                timing: 'Julho de 2026',
                days: 3,
                landmarks: ['Torre Eiffel'],
              },
            ],
            itinerary_mode: 'known',
            children_list: [{ id: 'child-1', name: 'Lia', age: 8 }],
            parents_list: ['Ana', 'Caio'],
            year: 2026,
            parsed_data: { destinations: [], landmarks: [] },
            selected_landmarks: [],
            landmark_activity_selections: [],
            itinerary_preferences: { days: 3, interests: [], pace: 'balanced' },
          },
        },
      },
    }),
  );
  await page.route('**/api/drafts/expired-draft', (route) => {
    updatedPayload = route.request().postDataJSON()?.payload || null;
    return route.fulfill({
      status: 200,
      json: {
        id: 'expired-draft',
        revision: 3,
        updated_at: '2026-07-21T10:01:00+00:00',
        payload: updatedPayload,
      },
    });
  });
  await page.route('**/api/guide-builder/expiredsession123', (route) =>
    route.fulfill({ status: 404, json: { detail: 'Builder session not found' } }),
  );

  const email = `expirada-${test.info().project.name}@example.test`;
  await authenticateLocalTestUser(page, email, 'Família Silva');
  await page.goto('/create', { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /Seu roteiro está pronto. Como você quer a capa?/ })).toBeVisible();
  await expect(page).toHaveURL(/\/create$/);
  await expect.poll(() => updatedPayload).not.toBeNull();
  expect(updatedPayload).toMatchObject({
    current_step: 6,
    builder_session_id: '',
    family_name: 'Silva',
    destination: 'Paris em Julho de 2026',
  });
});

test('family reviews the cover and queues the complete guide', async ({ page }) => {
  test.setTimeout(60_000);

  let coverAttempts = [];
  let coverSelected = null;
  let coverApproved = false;
  let generationQueued = false;
  let sessionRevision = 0;
  let builderCreates = 0;
  let generationRequests = 0;
  const revisionRequests = [];

  const sessionPayload = () => ({
    session_id: 'syntheticsession',
    created_at: '2026-08-20T00:00:00+00:00',
    expires_at: '2026-09-03T00:00:00+00:00',
    title: 'Família Aurora',
    revision: ++sessionRevision,
    layout_revision: 0,
    active_page_id: coverApproved ? null : 'cover',
    is_complete: false,
    ...(generationQueued
      ? {
          generation_job_id: 'syntheticjob',
          generation_requested_at: '2026-08-20T00:02:00+00:00',
        }
      : {}),
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
        requiredCopy: ['Família Aurora', 'Torre Eiffel', 'Coliseu'],
      }),
      pageState({
        id: 'landmark-1',
        kind: 'landmark',
        title: 'Torre Eiffel, França',
        position: 3,
        requiredCopy: ['Torre Eiffel', 'Paris, França'],
      }),
      pageState({
        id: 'activity-coloring',
        kind: 'landmark_activity',
        title: 'Página para colorir — Torre Eiffel',
        position: 4,
        requiredCopy: ['Torre Eiffel', 'Pinte sua aventura!'],
      }),
      pageState({
        id: 'best-memory',
        kind: 'best_memory',
        title: 'Minha melhor memória',
        position: 5,
        requiredCopy: ['Minha melhor memória', 'Data'],
      }),
    ],
  });

  await page.route('**/api/guides', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"guides":[]}' }),
  );
  await page.route('**/api/products/guide', (route) =>
    route.fulfill({
      status: 200,
      json: { enabled: false, amount_minor: 1999, currency: 'BRL' },
    }),
  );
  await page.route('**/api/drafts/current', (route) =>
    route.fulfill({
      status: 200,
      json: {
        draft: {
          id: 'visual-draft',
          revision: 1,
          updated_at: '2026-08-20T00:00:00+00:00',
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
                {
                  id: 'eiffel',
                  selection_id: 'eiffel',
                  destination_id: 'europe',
                  name: 'Torre Eiffel',
                  city: 'Paris',
                  country: 'França',
                },
                {
                  id: 'colosseum',
                  selection_id: 'colosseum',
                  destination_id: 'europe',
                  name: 'Coliseu',
                  city: 'Roma',
                  country: 'Itália',
                },
              ],
            },
            selected_landmarks: ['eiffel', 'colosseum'],
            landmark_activity_selections: [
              { landmark_selection_id: 'eiffel', activity_type: 'coloring', order: 1 },
            ],
            itinerary_preferences: { days: 5, interests: [], pace: 'balanced' },
            has_searched_landmarks: true,
          },
        },
      },
    }),
  );
  await page.route('**/api/drafts/visual-draft', (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: 'visual-draft',
        revision: 2,
        updated_at: '2026-08-20T00:01:00+00:00',
        payload: route.request().postDataJSON()?.payload || {},
      },
    }),
  );
  await page.route(/\/api\/guide-builder(?:\/.*)?$/, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const method = request.method();

    if (pathname === '/api/guide-builder' && method === 'POST') {
      builderCreates += 1;
      return route.fulfill({ status: 201, json: sessionPayload() });
    }
    if (pathname === '/api/guide-builder/syntheticsession' && method === 'GET') {
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (pathname.endsWith('/pages/cover/attempts') && method === 'POST') {
      const revisionInstruction = request.postDataJSON()?.revision_instruction || '';
      revisionRequests.push(revisionInstruction);
      const next = coverAttempts.length + 1;
      coverAttempts = [
        ...coverAttempts,
        attempt(`cover-${next}`, `cover-${next}.png`, revisionInstruction),
      ];
      coverSelected = `cover-${next}`;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (pathname.endsWith('/pages/cover/approve') && method === 'POST') {
      coverSelected = request.postDataJSON().attempt_id;
      coverApproved = true;
      return route.fulfill({ status: 200, json: sessionPayload() });
    }
    if (pathname.endsWith('/generation-jobs') && method === 'POST') {
      generationRequests += 1;
      generationQueued = true;
      return route.fulfill({
        status: 202,
        json: {
          job_id: 'syntheticjob',
          status: 'queued',
          stage: 'queued',
          progress: 0,
        },
      });
    }
    return route.abort('failed');
  });
  await page.route('**/api/jobs/syntheticjob', (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: 'syntheticjob',
        status: 'succeeded',
        stage: 'complete',
        progress: 100,
        result: {
          download_url: '/guide-builder/syntheticsession/pdf',
          filename: 'familia-aurora-minerva-travel.pdf',
          page_count: 5,
        },
      },
    }),
  );
  await page.route('**/guide-builder/syntheticsession/assets/*.png', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: onePixelPng }),
  );

  const email = `capa-${test.info().project.name}@example.test`;
  await authenticateLocalTestUser(page, email, 'Família Aurora');
  await page.goto('/create', { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Perfeito! Aqui está o resumo do seu roteiro' })).toBeVisible();
  await page.getByLabel('Confere: é assim que os nomes devem aparecer no livro.').check();
  await page.getByRole('button', { name: 'Criar e revisar a capa' }).click();

  await expect(page).toHaveURL(/\/create\?builder=syntheticsession$/);
  await expect(page.getByRole('heading', { name: 'Aprove a capa do seu guia' })).toBeVisible();
  await expect(page.getByText('Sua capa aparecerá aqui')).toBeVisible();

  await page.getByRole('button', { name: 'Gerar preview da capa' }).click();
  await expect(page.getByAltText('Preview da capa do guia')).toBeVisible();
  await page.getByPlaceholder(/use um estilo de livro infantil/).fill(
    'Deixe o céu mais claro e mantenha as mesmas pessoas.',
  );
  await page.getByRole('button', { name: 'Gerar nova versão' }).click();
  await expect(page.getByAltText('Preview da capa do guia')).toBeVisible();
  expect(revisionRequests).toEqual([
    '',
    'Deixe o céu mais claro e mantenha as mesmas pessoas.',
  ]);

  await page.getByRole('button', { name: 'Aprovar esta capa' }).click();
  await expect(page.getByRole('heading', { name: 'Capa aprovada' })).toBeVisible();
  await page.getByRole('button', { name: 'Criar guia completo' }).click();
  await expect(page.getByRole('heading', { name: 'Guia pronto e enviado' })).toBeVisible();

  expect(builderCreates).toBe(1);
  expect(generationRequests).toBe(1);
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);

  await test.info().attach(`progressive-guide-${test.info().project.name}`, {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  });
});
