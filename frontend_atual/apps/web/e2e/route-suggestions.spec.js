import { expect, test } from '@playwright/test';

const restoredDraftPayload = {
  schema_version: 2,
  current_step: 1,
  builder_session_id: '',
  family_name: 'Silva',
  destination: 'Rio de Janeiro, Brasil em Setembro de 2026 por 1 dia',
  destinations_list: [
    {
      id: 'restored-rio',
      place: 'Rio de Janeiro, Brasil',
      timing: 'Setembro de 2026',
      days: 1,
      landmarks: [],
    },
  ],
  itinerary_mode: 'suggested',
  children_list: [],
  parents_list: [],
  year: 2026,
  parsed_data: { destinations: [], landmarks: [] },
  selected_landmarks: [],
  landmark_activity_selections: [],
  itinerary_preferences: { days: 5, interests: ['parques', 'museus'], pace: 'light' },
  has_searched_landmarks: false,
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    globalThis.localStorage.setItem('minerva_local_session', JSON.stringify({
      id: 'local:rotas@example.test',
      email: 'rotas@example.test',
      name: 'Família Rotas',
      collectionName: 'users',
    }));
  });

  await page.route('**/api/guides', (route) => route.fulfill({ status: 200, json: { guides: [] } }));
  await page.route('**/api/family-profile', (route) => route.fulfill({
    status: 200,
    json: { profile: null },
  }));
  await page.route('**/api/drafts/current', (route) => route.fulfill({
    status: 200,
    json: {
      draft: {
        id: 'route-draft',
        revision: 1,
        updated_at: '2026-08-22T12:00:00Z',
        payload: restoredDraftPayload,
      },
    },
  }));
  await page.route('**/api/drafts/route-draft', (route) => route.fulfill({
    status: 200,
    json: {
      id: 'route-draft',
      revision: 2,
      updated_at: '2026-08-22T12:01:00Z',
      payload: route.request().postDataJSON()?.payload || restoredDraftPayload,
    },
  }));
});

test('natural-language route replaces a restored destination and explains the attraction step', async ({ page }) => {
  let suggestionPayload = null;
  await page.route('**/api/itinerary/routes/suggest', (route) => {
    suggestionPayload = route.request().postDataJSON();
    return route.fulfill({
      status: 200,
      json: {
        options: [
          {
            id: 'suggested-route-1',
            title: 'Sugestão equilibrada',
            summary: 'Roteiro leve com foco em parques e museus.',
            structured_destinations: [
              { id: 'suggested-1', place: 'Paris', timing: '', days: 3 },
              { id: 'suggested-2', place: 'Londres', timing: '', days: 2 },
            ],
          },
        ],
      },
    });
  });

  await page.goto('/create', { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Para onde vai ser a aventura?' })).toBeVisible();
  await expect(page.getByText(/no passo 3, sugerimos os pontos turísticos/i)).toBeVisible();

  await page.getByLabel('O que vocês imaginam para essa viagem?')
    .fill('Queremos Paris e Londres com parques, museus e ritmo leve.');
  await page.getByRole('button', { name: 'Buscar sugestões' }).click();

  await expect(page.getByText('1. Paris · 3 dias')).toBeVisible();
  await expect(page.getByText('2. Londres · 2 dias')).toBeVisible();
  expect(suggestionPayload.trip_idea).toContain('Paris e Londres');
  expect(suggestionPayload.structured_destinations).toEqual([]);

  await page.getByRole('button', { name: 'Usar rota' }).click();
  await expect(page.getByText(/Rota aplicada: Paris → Londres/)).toBeVisible();
  await expect(page.getByLabel('Pra onde vocês vão?').nth(0)).toHaveValue('Paris');
  await expect(page.getByLabel('Pra onde vocês vão?').nth(1)).toHaveValue('Londres');
});

test('empty natural-language search shows a useful inline error', async ({ page }) => {
  await page.goto('/create', { waitUntil: 'domcontentloaded' });
  await page.getByLabel('O que vocês imaginam para essa viagem?').fill('   ');
  await page.getByRole('button', { name: 'Buscar sugestões' }).click();

  await expect(page.getByRole('alert')).toHaveText(
    'Conte pelo menos quais cidades ou regiões vocês querem conhecer.'
  );
  await expect(page.getByLabel('O que vocês imaginam para essa viagem?')).toBeFocused();
});
