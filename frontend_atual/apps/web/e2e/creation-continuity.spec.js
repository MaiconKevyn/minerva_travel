import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const draftPayload = {
  schema_version: 2,
  current_step: 4,
  builder_session_id: '',
  family_name: 'Horizonte',
  destination: 'Paris em setembro de 2026',
  destinations_list: [
    {
      id: 'paris',
      place: 'Paris',
      timing: 'Setembro de 2026',
      days: 4,
      landmarks: ['Museu do Louvre'],
    },
  ],
  itinerary_mode: 'known',
  children_list: [{ id: 'child-1', name: 'Lia', age: 8 }],
  parents_list: ['Ana', 'Caio'],
  year: 2026,
  parsed_data: {
    destinations: [{ id: 'paris', city: 'Paris', country: 'França' }],
    landmarks: [
      {
        id: 'louvre-card',
        selection_id: 'paris:louvre',
        destination_id: 'paris',
        name: 'Museu do Louvre',
        city: 'Paris',
        country: 'França',
      },
    ],
  },
  selected_landmarks: ['paris:louvre'],
  landmark_activity_selections: [],
  itinerary_preferences: { days: 4, interests: [], pace: 'balanced' },
  has_searched_landmarks: true,
  expected_cover_family_member_count: 3,
};

const authenticateLocalTestUser = async (page) => {
  await page.addInitScript(() => {
    globalThis.localStorage.setItem('minerva_local_session', JSON.stringify({
      id: 'local:continuidade@example.test',
      email: 'continuidade@example.test',
      name: 'Família Horizonte',
      collectionName: 'users',
    }));
  });
};

const mockContinuityApis = async (page) => {
  let deleteRequests = 0;

  await page.route('**/api/drafts/current', (route) => route.fulfill({
    status: 200,
    json: {
      draft: {
        id: 'draft-continuity',
        revision: 2,
        updated_at: '2026-08-20T10:00:00Z',
        payload: draftPayload,
      },
    },
  }));
  await page.route('**/api/drafts/draft-continuity', (route) => {
    if (route.request().method() === 'DELETE') {
      deleteRequests += 1;
      return route.fulfill({ status: 200, json: { deleted: true } });
    }
    return route.fulfill({
      status: 200,
      json: {
        id: 'draft-continuity',
        revision: 3,
        updated_at: '2026-08-20T10:01:00Z',
        payload: route.request().postDataJSON()?.payload || draftPayload,
      },
    });
  });
  await page.route('**/api/family-profile', (route) => route.fulfill({
    status: 200,
    json: { profile: null },
  }));
  await page.route('**/api/guides', (route) => route.fulfill({
    status: 200,
    json: { guides: [] },
  }));
  await page.route('**/api/jobs', (route) => route.fulfill({
    status: 200,
    json: { jobs: [] },
  }));

  return { getDeleteRequests: () => deleteRequests };
};

const assertNoHorizontalOverflow = async (page) => {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
};

test.beforeEach(async ({ page }) => {
  await authenticateLocalTestUser(page);
});

test('restored creation explains progress and safely continues later', async ({ page }) => {
  await mockContinuityApis(page);
  await page.goto('/create', { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: 'Quem vai viajar' })).toBeVisible();
  await expect(page.getByText(/Próximo:/)).toContainText('Atividades');
  await expect(page.getByRole('progressbar', { name: 'Progresso da criação do guia' }))
    .toHaveAttribute('aria-valuenow', '3');
  await expect(page.getByText('Seu rascunho foi recuperado e está salvo.')).toBeVisible();
  await assertNoHorizontalOverflow(page);

  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);

  const screenshotPath = test.info().outputPath(`creation-continuity-${test.info().project.name}.png`);
  await page.screenshot({ fullPage: true, path: screenshotPath });
  await test.info().attach(`creation-continuity-${test.info().project.name}`, {
    path: screenshotPath,
    contentType: 'image/png',
  });

  await page.getByRole('button', { name: 'Continuar depois' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'Olá, Família Horizonte!' })).toBeVisible();
});

test('discard requires explicit confirmation before deleting the draft', async ({ page }) => {
  const requests = await mockContinuityApis(page);
  await page.goto('/create', { waitUntil: 'domcontentloaded' });

  await page.getByRole('button', { name: 'Descartar', exact: true }).click();
  await expect(page.getByRole('alertdialog')).toBeVisible();
  expect(requests.getDeleteRequests()).toBe(0);

  await page.getByRole('button', { name: 'Manter rascunho' }).click();
  await expect(page.getByRole('alertdialog')).toBeHidden();
  expect(requests.getDeleteRequests()).toBe(0);

  await page.getByRole('button', { name: 'Descartar', exact: true }).click();
  await page.getByRole('button', { name: 'Descartar definitivamente' }).click();
  await expect(page.getByRole('heading', { name: 'Destinos da viagem' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continuar depois' })).toHaveCount(0);
  expect(requests.getDeleteRequests()).toBe(1);
});

test.describe('creation continuity at the 390 px narrow boundary', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('keeps progress and draft actions visible without horizontal overflow', async ({ page }) => {
    await mockContinuityApis(page);
    await page.goto('/create', { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Quem vai viajar' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continuar depois' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Descartar', exact: true })).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});
